#!/usr/bin/env python3
"""
Wizardry 6 Wall Renderer - Test Area Focus
Renders walls in the specific test area we've been working with.
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

def analyze_test_area(cells):
    """
    Analyze the test area (2x2 block) walls.
    Based on our tests, this is around cells 30 and 39 in the file.
    """
    print("\nTest Area Wall Analysis:")
    print("="*60)

    # Cell 30 - horizontal walls
    cell_30 = cells[30]
    print("\nCell 30 (Horizontal walls):")
    print(f"  Byte 1: 0x{cell_30[1]:02X} (bottom row)")
    print(f"  Byte 3: 0x{cell_30[3]:02X} (middle row)")
    print(f"  Byte 5: 0x{cell_30[5]:02X} (top row)")

    # Cell 39 - vertical walls
    cell_39 = cells[39]
    print("\nCell 39 (Vertical and other walls):")
    for byte_idx in [15, 17]:
        print(f"  Byte {byte_idx}: 0x{cell_39[byte_idx]:02X}")

    # Show which walls are present
    print("\nDecoded walls in test area:")

    # Horizontal walls (Cell 30)
    for byte_idx, label in [(1, "Bottom"), (3, "Middle"), (5, "Top")]:
        val = cell_30[byte_idx]
        left = "LEFT" if (val & 0x20) else "----"
        right = "RIGHT" if (val & 0x80) else "-----"
        print(f"  {label} horizontal: {left} | {right}")

    # Vertical walls (from right/left edge tests)
    print("\nVertical edge walls (across map height):")

    # Check cells 30-39 for vertical walls
    vertical_left = []
    vertical_right = []

    for cell_idx in [30, 35, 36, 37, 38, 39]:
        cell = cells[cell_idx]
        for byte_idx in range(1, 20, 2):
            if cell[byte_idx] & 0x20:  # Bit 5 = left
                vertical_left.append((cell_idx, byte_idx))
            if cell[byte_idx] & 0x80:  # Bit 7 = right
                vertical_right.append((cell_idx, byte_idx))

    print(f"  Left edge segments: {len(vertical_left)}")
    print(f"  Right edge segments: {len(vertical_right)}")

def render_map(cells, cell_size=40):
    """Render map focusing on test area."""

    pygame.init()

    # Focus on smaller area for better visibility
    view_width = 10
    view_height = 10

    padding = 80
    window_width = view_width * cell_size + padding * 2
    window_height = view_height * cell_size + padding * 2 + 100

    screen = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Wizardry 6 - Test Area Walls")

    # Colors
    COLOR_BG = (250, 250, 245)
    COLOR_FLOOR = (230, 230, 220)
    COLOR_WALL = (30, 30, 30)
    COLOR_TEST_WALL = (200, 50, 50)  # Red for test walls
    COLOR_GRID = (200, 200, 190)
    COLOR_TEXT = (0, 0, 0)

    font = pygame.font.Font(None, 24)
    font_small = pygame.font.Font(None, 16)

    # Analyze test area
    analyze_test_area(cells)

    # Extract test walls from Cell 30
    cell_30 = cells[30]
    test_walls = {
        'bottom': (bool(cell_30[1] & 0x20), bool(cell_30[1] & 0x80)),
        'middle': (bool(cell_30[3] & 0x20), bool(cell_30[3] & 0x80)),
        'top': (bool(cell_30[5] & 0x20), bool(cell_30[5] & 0x80)),
    }

    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    running = False

        screen.fill(COLOR_BG)

        # Title
        title = font.render("Test Area - 2x2 Block Walls", True, COLOR_TEXT)
        screen.blit(title, (padding, 10))

        # Draw grid
        for row in range(view_height + 1):
            y = padding + row * cell_size
            pygame.draw.line(screen, COLOR_GRID,
                           (padding, y),
                           (padding + view_width * cell_size, y), 1)

        for col in range(view_width + 1):
            x = padding + col * cell_size
            pygame.draw.line(screen, COLOR_GRID,
                           (x, padding),
                           (x, padding + view_height * cell_size), 1)

        # Draw floor
        for row in range(view_height):
            for col in range(view_width):
                x = padding + col * cell_size
                y = padding + row * cell_size
                pygame.draw.rect(screen, COLOR_FLOOR,
                               (x + 1, y + 1, cell_size - 2, cell_size - 2))

        # Draw test area walls (2x2 block in center)
        # Position the test block at rows 4-5, cols 4-5
        test_row = 4
        test_col = 4

        wall_thickness = 4

        # Top horizontal walls (byte 5)
        if test_walls['top'][0]:  # Left
            x = padding + test_col * cell_size
            y = padding + test_row * cell_size
            pygame.draw.line(screen, COLOR_TEST_WALL,
                           (x, y), (x + cell_size, y), wall_thickness)

        if test_walls['top'][1]:  # Right
            x = padding + (test_col + 1) * cell_size
            y = padding + test_row * cell_size
            pygame.draw.line(screen, COLOR_TEST_WALL,
                           (x, y), (x + cell_size, y), wall_thickness)

        # Middle horizontal walls (byte 3)
        if test_walls['middle'][0]:  # Left
            x = padding + test_col * cell_size
            y = padding + (test_row + 1) * cell_size
            pygame.draw.line(screen, COLOR_TEST_WALL,
                           (x, y), (x + cell_size, y), wall_thickness)

        if test_walls['middle'][1]:  # Right
            x = padding + (test_col + 1) * cell_size
            y = padding + (test_row + 1) * cell_size
            pygame.draw.line(screen, COLOR_TEST_WALL,
                           (x, y), (x + cell_size, y), wall_thickness)

        # Bottom horizontal walls (byte 1)
        if test_walls['bottom'][0]:  # Left
            x = padding + test_col * cell_size
            y = padding + (test_row + 2) * cell_size
            pygame.draw.line(screen, COLOR_TEST_WALL,
                           (x, y), (x + cell_size, y), wall_thickness)

        if test_walls['bottom'][1]:  # Right
            x = padding + (test_col + 1) * cell_size
            y = padding + (test_row + 2) * cell_size
            pygame.draw.line(screen, COLOR_TEST_WALL,
                           (x, y), (x + cell_size, y), wall_thickness)

        # Draw labels
        info_y = padding + view_height * cell_size + 20

        info = [
            "Red walls = Decoded test walls",
            f"Cell 30 Byte 1: 0x{cell_30[1]:02X} (bottom)",
            f"Cell 30 Byte 3: 0x{cell_30[3]:02X} (middle)",
            f"Cell 30 Byte 5: 0x{cell_30[5]:02X} (top)",
        ]

        for i, text in enumerate(info):
            rendered = font_small.render(text, True, COLOR_TEXT)
            screen.blit(rendered, (padding, info_y + i * 18))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

def main():
    filepath = Path("gamedata/NEWGAME.DBS")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print("Wizardry 6 - Test Area Wall Renderer")
    print("="*60)

    cells = read_map_data(filepath)
    render_map(cells)

if __name__ == "__main__":
    main()
