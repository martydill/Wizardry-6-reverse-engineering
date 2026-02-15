#!/usr/bin/env python3
"""
Pygame wall renderer using the decoded wall format.
Based on discovered pattern:
- 20 bytes per cell
- Column-major storage (cell = col * 20 + row)
- ODD bytes encode walls
- Bit 3 = Vertical walls
- Bit 5 = Horizontal walls
- Bit 7 = Unknown/Special walls
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

def get_cell_walls(cell_data):
    """
    Extract wall information from a cell.
    Returns a dict with all wall bits found.
    """
    walls = {
        'vertical': [],    # Bit 3 walls
        'horizontal': [],  # Bit 5 walls
        'special': [],     # Bit 7 walls
        'other': []        # Other bits
    }

    # Check all ODD bytes for wall bits
    for byte_idx in range(1, 20, 2):  # 1, 3, 5, 7, 9, 11, 13, 15, 17, 19
        byte_val = cell_data[byte_idx]

        if byte_val & 0x08:  # Bit 3
            walls['vertical'].append((byte_idx, 3))
        if byte_val & 0x20:  # Bit 5
            walls['horizontal'].append((byte_idx, 5))
        if byte_val & 0x80:  # Bit 7
            walls['special'].append((byte_idx, 7))

        # Check other bits for debugging
        for bit in [0, 1, 2, 4, 6]:
            if byte_val & (1 << bit):
                walls['other'].append((byte_idx, bit))

    return walls

def render_map(cells, cell_size=32):
    """Render the map with decoded walls."""

    # Initialize pygame
    pygame.init()

    # Map dimensions
    map_width = 20
    map_height = 20

    # Calculate window size
    padding = 60
    window_width = map_width * cell_size + padding * 2
    window_height = map_height * cell_size + padding * 2 + 100  # Extra space for info

    # Create window
    screen = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Wizardry 6 - Decoded Walls")

    # Colors
    COLOR_BG = (250, 250, 250)
    COLOR_GRID = (220, 220, 220)
    COLOR_VERTICAL = (0, 0, 255)      # Blue for vertical walls
    COLOR_HORIZONTAL = (255, 0, 0)    # Red for horizontal walls
    COLOR_SPECIAL = (255, 0, 255)     # Magenta for special/unknown
    COLOR_TEXT = (0, 0, 0)
    COLOR_TEST_CELL = (255, 255, 200) # Light yellow for test cells

    # Font
    font = pygame.font.Font(None, 24)
    font_small = pygame.font.Font(None, 18)
    font_tiny = pygame.font.Font(None, 14)

    # Track cells with walls for statistics
    cells_with_walls = set()
    wall_stats = {'vertical': 0, 'horizontal': 0, 'special': 0}

    # Pre-process to find all cells with walls
    for i in range(400):
        walls = get_cell_walls(cells[i])
        if walls['vertical'] or walls['horizontal'] or walls['special']:
            cells_with_walls.add(i)
            wall_stats['vertical'] += len(walls['vertical'])
            wall_stats['horizontal'] += len(walls['horizontal'])
            wall_stats['special'] += len(walls['special'])

    # Main loop
    clock = pygame.time.Clock()
    running = True
    show_debug = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_d:
                    show_debug = not show_debug

        # Clear screen
        screen.fill(COLOR_BG)

        # Draw title
        title = font.render("Wizardry 6 - Decoded Wall Format", True, COLOR_TEXT)
        screen.blit(title, (padding, 10))

        # Draw grid
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

        # Draw cells (column-major)
        for col in range(map_width):
            for row in range(map_height):
                cell_idx = col * 20 + row  # Column-major!
                cell_data = cells[cell_idx]

                # Screen position
                x = padding + col * cell_size
                y = padding + row * cell_size

                # Highlight test cells (30 and 39)
                if cell_idx in [30, 39]:
                    pygame.draw.rect(screen, COLOR_TEST_CELL,
                                   (x + 1, y + 1, cell_size - 2, cell_size - 2))

                # Get walls
                walls = get_cell_walls(cell_data)

                # Draw wall indicators (small colored squares in cell)
                indicator_size = 4
                indicator_offset = 5

                if walls['vertical']:
                    # Blue square for vertical walls
                    pygame.draw.rect(screen, COLOR_VERTICAL,
                                   (x + indicator_offset, y + indicator_offset,
                                    indicator_size, indicator_size))

                if walls['horizontal']:
                    # Red square for horizontal walls
                    pygame.draw.rect(screen, COLOR_HORIZONTAL,
                                   (x + cell_size - indicator_offset - indicator_size,
                                    y + indicator_offset,
                                    indicator_size, indicator_size))

                if walls['special']:
                    # Magenta square for special walls
                    pygame.draw.rect(screen, COLOR_SPECIAL,
                                   (x + indicator_offset,
                                    y + cell_size - indicator_offset - indicator_size,
                                    indicator_size, indicator_size))

                # Show cell index for test cells
                if cell_idx in [30, 39]:
                    text = font_tiny.render(f"{cell_idx}", True, COLOR_TEXT)
                    screen.blit(text, (x + 2, y + cell_size - 12))

        # Draw row labels
        for row in range(map_height):
            y = padding + row * cell_size + cell_size // 2
            text = font_tiny.render(f"{row}", True, COLOR_TEXT)
            screen.blit(text, (5, y - 6))

        # Draw column labels
        for col in range(map_width):
            x = padding + col * cell_size + cell_size // 2
            text = font_tiny.render(f"{col}", True, COLOR_TEXT)
            screen.blit(text, (x - 4, padding - 20))

        # Draw statistics
        stats_y = padding + map_height * cell_size + 20

        stats_text = [
            f"Cells with walls: {len(cells_with_walls)}/400",
            f"Vertical walls (bit 3): {wall_stats['vertical']}",
            f"Horizontal walls (bit 5): {wall_stats['horizontal']}",
            f"Special/Unknown (bit 7): {wall_stats['special']}",
        ]

        for i, text in enumerate(stats_text):
            rendered = font_small.render(text, True, COLOR_TEXT)
            screen.blit(rendered, (padding, stats_y + i * 20))

        # Draw legend
        legend_y = stats_y + 90
        legend_x = padding

        # Vertical
        pygame.draw.rect(screen, COLOR_VERTICAL, (legend_x, legend_y, 12, 12))
        text = font_small.render("= Vertical walls (bit 3)", True, COLOR_TEXT)
        screen.blit(text, (legend_x + 18, legend_y - 2))

        # Horizontal
        legend_x += 200
        pygame.draw.rect(screen, COLOR_HORIZONTAL, (legend_x, legend_y, 12, 12))
        text = font_small.render("= Horizontal walls (bit 5)", True, COLOR_TEXT)
        screen.blit(text, (legend_x + 18, legend_y - 2))

        # Special
        legend_x += 230
        pygame.draw.rect(screen, COLOR_SPECIAL, (legend_x, legend_y, 12, 12))
        text = font_small.render("= Special/Unknown (bit 7)", True, COLOR_TEXT)
        screen.blit(text, (legend_x + 18, legend_y - 2))

        # Instructions
        info = font_small.render("Press ESC/Q to quit | D for debug", True, COLOR_TEXT)
        screen.blit(info, (window_width - 280, 10))

        # Update display
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

def main():
    filepath = Path("gamedata/NEWGAME.DBS")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print("Loading Wizardry 6 map data...")
    print("Format: 20 bytes per cell, column-major storage")
    print()

    cells = read_map_data(filepath)

    print("Starting pygame renderer...")
    print("Controls:")
    print("  ESC or Q - Quit")
    print("  D - Toggle debug info")
    print()
    print("Wall encoding:")
    print("  Bit 3 (0x08) = Vertical walls (blue)")
    print("  Bit 5 (0x20) = Horizontal walls (red)")
    print("  Bit 7 (0x80) = Special/Unknown (magenta)")
    print()
    print("Test cells 30 and 39 are highlighted in yellow")
    print()

    render_map(cells)

if __name__ == "__main__":
    main()
