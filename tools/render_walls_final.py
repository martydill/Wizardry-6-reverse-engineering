#!/usr/bin/env python3
"""
Wizardry 6 Wall Renderer - Using Fully Decoded Format
Renders actual walls based on discovered encoding:
  - Byte position = Y-coordinate
  - Bit 5 = Left wall
  - Bit 7 = Right wall
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
    for i in range(400):  # 20x20 grid
        start = i * bytes_per_cell
        end = start + bytes_per_cell
        if end <= len(data):
            cells.append(data[start:end])
        else:
            cells.append(bytes([0] * bytes_per_cell))

    return cells

def decode_walls_for_cell(cell_data):
    """
    Decode wall information from cell data.
    Returns dict of walls present.
    """
    walls = {
        'horizontal': {},  # {byte_idx: (has_left, has_right)}
        'vertical': {}     # {byte_idx: (has_left, has_right)}
    }

    # Check all ODD bytes (1, 3, 5, 7, 9, 11, 13, 15, 17, 19)
    for byte_idx in range(1, 20, 2):
        byte_val = cell_data[byte_idx]

        has_left = bool(byte_val & 0x20)   # Bit 5
        has_right = bool(byte_val & 0x80)  # Bit 7

        if has_left or has_right:
            # For now, treat all as potential walls
            # We'll determine horizontal vs vertical by context
            walls['vertical'][byte_idx] = (has_left, has_right)

    return walls

def build_wall_map(cells):
    """
    Build a complete wall map for the entire grid.
    Returns: grid of walls for rendering
    """
    # Wall map: [row][col] = {N, S, E, W} walls
    wall_map = [[{'N': False, 'S': False, 'E': False, 'W': False}
                 for _ in range(20)] for _ in range(20)]

    # Process each cell
    for cell_idx in range(400):
        col = cell_idx // 20  # Column-major
        row = cell_idx % 20

        cell_data = cells[cell_idx]

        # Check all odd bytes for walls
        for byte_idx in range(1, 20, 2):
            byte_val = cell_data[byte_idx]

            if byte_val & 0x20:  # Bit 5 = left
                wall_map[row][col]['W'] = True
            if byte_val & 0x80:  # Bit 7 = right
                wall_map[row][col]['E'] = True

    return wall_map

def render_map(cells, cell_size=32):
    """Render the map with actual walls."""

    # Initialize pygame
    pygame.init()

    # Map dimensions
    map_width = 20
    map_height = 20

    # Calculate window size
    padding = 60
    window_width = map_width * cell_size + padding * 2
    window_height = map_height * cell_size + padding * 2 + 80

    # Create window
    screen = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Wizardry 6 - Decoded Walls")

    # Colors
    COLOR_BG = (245, 245, 240)      # Light beige background
    COLOR_FLOOR = (220, 220, 210)   # Slightly darker floor
    COLOR_WALL = (40, 40, 40)       # Dark gray walls
    COLOR_GRID = (200, 200, 195)    # Light grid
    COLOR_TEXT = (0, 0, 0)

    # Font
    font = pygame.font.Font(None, 24)
    font_small = pygame.font.Font(None, 18)

    # Build wall map
    print("Building wall map...")
    wall_map = build_wall_map(cells)

    # Count walls
    total_walls = 0
    for row in range(map_height):
        for col in range(map_width):
            total_walls += sum(wall_map[row][col].values())

    print(f"Total walls found: {total_walls}")

    # Main loop
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

        # Clear screen
        screen.fill(COLOR_BG)

        # Draw title
        title = font.render("Wizardry 6 - Decoded Wall Map", True, COLOR_TEXT)
        screen.blit(title, (padding, 10))

        # Draw floor tiles
        for row in range(map_height):
            for col in range(map_width):
                x = padding + col * cell_size
                y = padding + row * cell_size
                pygame.draw.rect(screen, COLOR_FLOOR,
                               (x + 1, y + 1, cell_size - 2, cell_size - 2))

        # Draw grid (optional)
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

        # Draw walls (thick lines)
        wall_thickness = 4

        for row in range(map_height):
            for col in range(map_width):
                x = padding + col * cell_size
                y = padding + row * cell_size

                walls = wall_map[row][col]

                # North wall (top edge)
                if walls['N']:
                    pygame.draw.line(screen, COLOR_WALL,
                                   (x, y),
                                   (x + cell_size, y),
                                   wall_thickness)

                # South wall (bottom edge)
                if walls['S']:
                    pygame.draw.line(screen, COLOR_WALL,
                                   (x, y + cell_size),
                                   (x + cell_size, y + cell_size),
                                   wall_thickness)

                # West wall (left edge)
                if walls['W']:
                    pygame.draw.line(screen, COLOR_WALL,
                                   (x, y),
                                   (x, y + cell_size),
                                   wall_thickness)

                # East wall (right edge)
                if walls['E']:
                    pygame.draw.line(screen, COLOR_WALL,
                                   (x + cell_size, y),
                                   (x + cell_size, y + cell_size),
                                   wall_thickness)

        # Draw row labels
        for row in range(map_height):
            y = padding + row * cell_size + cell_size // 2
            text = font_small.render(f"{row}", True, COLOR_TEXT)
            screen.blit(text, (10, y - 8))

        # Draw column labels
        for col in range(map_width):
            x = padding + col * cell_size + cell_size // 2
            text = font_small.render(f"{col}", True, COLOR_TEXT)
            screen.blit(text, (x - 8, padding - 20))

        # Draw info
        info_y = padding + map_height * cell_size + 20

        info_texts = [
            f"Total walls: {total_walls}",
            f"Grid: {'ON' if show_grid else 'OFF'} (press G to toggle)",
            "Press ESC or Q to quit"
        ]

        for i, text in enumerate(info_texts):
            rendered = font_small.render(text, True, COLOR_TEXT)
            screen.blit(rendered, (padding, info_y + i * 20))

        # Update display
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

def main():
    filepath = Path("gamedata/NEWGAME.DBS")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print("Wizardry 6 Wall Renderer - Using Decoded Format")
    print("="*60)
    print()
    print("Loading map data...")
    print("Format: 20 bytes per cell, column-major storage")
    print()

    cells = read_map_data(filepath)

    print("Wall encoding:")
    print("  Byte position = Y-coordinate")
    print("  Bit 5 = Left wall")
    print("  Bit 7 = Right wall")
    print()
    print("Starting renderer...")
    print()
    print("Controls:")
    print("  G - Toggle grid")
    print("  ESC or Q - Quit")
    print()

    render_map(cells)

if __name__ == "__main__":
    main()
