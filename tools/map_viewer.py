"""Map viewer — 2D top-down visualization of dungeon levels.

Usage:
    python -m tools.map_viewer gamedata/SCENARIO.DBS
    python -m tools.map_viewer --test  # display test map
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import pygame

from bane.data.enums import Direction, TileSpecial, WallType
from bane.data.map_loader import DungeonMap, MapPosition
from bane.data.models import DungeonLevel, TileData


TILE_SIZE = 24
WALL_THICKNESS = 2

# Colors
BG_COLOR = (20, 20, 30)
FLOOR_COLOR = (50, 50, 60)
WALL_COLOR = (180, 160, 140)
DOOR_COLOR = (140, 100, 50)
SECRET_COLOR = (80, 80, 160)
PLAYER_COLOR = (0, 255, 100)
STAIRS_UP_COLOR = (100, 200, 100)
STAIRS_DOWN_COLOR = (200, 100, 100)
TELEPORT_COLOR = (100, 100, 255)
SPECIAL_COLOR = (255, 200, 0)
GRID_COLOR = (35, 35, 45)
VISITED_COLOR = (60, 60, 75)


def create_test_dungeon() -> DungeonMap:
    """Create a small test dungeon for development."""
    dungeon = DungeonMap()

    level = DungeonLevel(level_id=0, name="Test Level", width=8, height=8)
    level.tiles = []

    for y in range(8):
        row = []
        for x in range(8):
            tile = TileData(x=x, y=y)
            # Outer walls
            if y == 0:
                tile.north_wall = WallType.WALL
            if y == 7:
                tile.south_wall = WallType.WALL
            if x == 0:
                tile.west_wall = WallType.WALL
            if x == 7:
                tile.east_wall = WallType.WALL
            # Some interior walls
            if x == 3 and y < 5:
                tile.east_wall = WallType.WALL
            if x == 4 and y < 5:
                tile.west_wall = WallType.WALL
            # Door
            if x == 3 and y == 3:
                tile.east_wall = WallType.DOOR
            if x == 4 and y == 3:
                tile.west_wall = WallType.DOOR
            # Secret door
            if x == 3 and y == 1:
                tile.east_wall = WallType.SECRET
            if x == 4 and y == 1:
                tile.west_wall = WallType.SECRET
            # Specials
            if x == 1 and y == 1:
                tile.special = TileSpecial.STAIRS_DOWN
            if x == 6 and y == 6:
                tile.special = TileSpecial.STAIRS_UP
            if x == 6 and y == 1:
                tile.special = TileSpecial.TELEPORTER
            if x == 2 and y == 5:
                tile.special = TileSpecial.SPINNER
            row.append(tile)
        level.tiles.append(row)

    dungeon.load_levels({0: level})
    return dungeon


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bane-map",
        description="View Wizardry 6 dungeon maps",
    )
    parser.add_argument("file", type=Path, nargs="?", help="Path to SCENARIO.DBS")
    parser.add_argument("--test", action="store_true", help="Show test dungeon")
    parser.add_argument("--level", type=int, default=0, help="Level to display")
    parser.add_argument("--ascii", action="store_true", help="ASCII output instead of GUI")
    args = parser.parse_args()

    if args.test:
        dungeon = create_test_dungeon()
    elif args.file:
        from bane.data.scenario_parser import ScenarioParser
        scenario_parser = ScenarioParser(args.file)
        try:
            scenario = scenario_parser.parse()
            dungeon = DungeonMap()
            dungeon.load_levels(scenario.dungeon_levels)
        except Exception as e:
            print(f"Error loading scenario: {e}")
            print("Using test dungeon instead")
            dungeon = create_test_dungeon()
    else:
        print("Specify a file or use --test")
        sys.exit(1)

    if args.ascii:
        print(dungeon.get_ascii_map(args.level))
        return

    # GUI mode
    level = dungeon.get_level(args.level)
    if level is None:
        print(f"Level {args.level} not found. Available: {dungeon.level_ids}")
        sys.exit(1)

    pygame.init()
    win_w = max(640, level.width * TILE_SIZE + 40)
    win_h = max(480, level.height * TILE_SIZE + 80)
    screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
    pygame.display.set_caption(f"Bane Engine — Map Viewer: {level.name}")
    font = pygame.font.Font(None, 20)

    # Camera offset for scrolling
    cam_x, cam_y = 20, 40
    player_pos = MapPosition(level=args.level, x=1, y=1, facing=Direction.NORTH)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                # Move player marker
                elif event.key == pygame.K_UP:
                    new = MapPosition(player_pos.level, player_pos.x, player_pos.y - 1, player_pos.facing)
                    if dungeon.get_tile(new.level, new.x, new.y):
                        player_pos = new
                elif event.key == pygame.K_DOWN:
                    new = MapPosition(player_pos.level, player_pos.x, player_pos.y + 1, player_pos.facing)
                    if dungeon.get_tile(new.level, new.x, new.y):
                        player_pos = new
                elif event.key == pygame.K_LEFT:
                    new = MapPosition(player_pos.level, player_pos.x - 1, player_pos.y, player_pos.facing)
                    if dungeon.get_tile(new.level, new.x, new.y):
                        player_pos = new
                elif event.key == pygame.K_RIGHT:
                    new = MapPosition(player_pos.level, player_pos.x + 1, player_pos.y, player_pos.facing)
                    if dungeon.get_tile(new.level, new.x, new.y):
                        player_pos = new

        screen.fill(BG_COLOR)

        # Title
        title = font.render(
            f"Level {level.level_id}: {level.name} ({level.width}x{level.height})",
            True, (200, 200, 200),
        )
        screen.blit(title, (10, 10))

        # Draw tiles
        for y in range(level.height):
            for x in range(level.width):
                tile = level.tiles[y][x]
                sx = cam_x + x * TILE_SIZE
                sy = cam_y + y * TILE_SIZE

                # Floor
                pygame.draw.rect(screen, FLOOR_COLOR, (sx + 1, sy + 1, TILE_SIZE - 2, TILE_SIZE - 2))

                # Special tiles
                special_colors = {
                    TileSpecial.STAIRS_UP: STAIRS_UP_COLOR,
                    TileSpecial.STAIRS_DOWN: STAIRS_DOWN_COLOR,
                    TileSpecial.TELEPORTER: TELEPORT_COLOR,
                    TileSpecial.SPINNER: (255, 150, 0),
                    TileSpecial.DARK_ZONE: (40, 40, 40),
                    TileSpecial.DAMAGE_FLOOR: (200, 50, 50),
                }
                if tile.special in special_colors:
                    color = special_colors[tile.special]
                    pygame.draw.rect(
                        screen, color,
                        (sx + 4, sy + 4, TILE_SIZE - 8, TILE_SIZE - 8),
                    )

                # Walls
                wall_styles = {
                    WallType.WALL: (WALL_COLOR, WALL_THICKNESS),
                    WallType.DOOR: (DOOR_COLOR, WALL_THICKNESS),
                    WallType.SECRET: (SECRET_COLOR, 1),
                }

                # North wall
                if tile.north_wall in wall_styles:
                    color, thick = wall_styles[tile.north_wall]
                    pygame.draw.line(screen, color, (sx, sy), (sx + TILE_SIZE, sy), thick)

                # South wall
                if tile.south_wall in wall_styles:
                    color, thick = wall_styles[tile.south_wall]
                    pygame.draw.line(
                        screen, color,
                        (sx, sy + TILE_SIZE), (sx + TILE_SIZE, sy + TILE_SIZE), thick,
                    )

                # West wall
                if tile.west_wall in wall_styles:
                    color, thick = wall_styles[tile.west_wall]
                    pygame.draw.line(screen, color, (sx, sy), (sx, sy + TILE_SIZE), thick)

                # East wall
                if tile.east_wall in wall_styles:
                    color, thick = wall_styles[tile.east_wall]
                    pygame.draw.line(
                        screen, color,
                        (sx + TILE_SIZE, sy), (sx + TILE_SIZE, sy + TILE_SIZE), thick,
                    )

        # Draw player marker
        px = cam_x + player_pos.x * TILE_SIZE + TILE_SIZE // 2
        py = cam_y + player_pos.y * TILE_SIZE + TILE_SIZE // 2
        pygame.draw.circle(screen, PLAYER_COLOR, (px, py), TILE_SIZE // 4)
        # Direction indicator
        dx, dy = player_pos.facing.dx, player_pos.facing.dy
        pygame.draw.line(
            screen, PLAYER_COLOR,
            (px, py),
            (px + dx * TILE_SIZE // 3, py + dy * TILE_SIZE // 3),
            2,
        )

        # Info bar
        info = font.render(
            f"Player: ({player_pos.x}, {player_pos.y}) | Arrow keys: Move | ESC: Quit",
            True, (150, 150, 150),
        )
        screen.blit(info, (10, win_h - 25))

        # Legend
        legend_x = win_w - 160
        legend_items = [
            (WALL_COLOR, "Wall"),
            (DOOR_COLOR, "Door"),
            (SECRET_COLOR, "Secret"),
            (STAIRS_UP_COLOR, "Stairs Up"),
            (STAIRS_DOWN_COLOR, "Stairs Down"),
            (TELEPORT_COLOR, "Teleporter"),
            (PLAYER_COLOR, "Player"),
        ]
        for i, (color, label) in enumerate(legend_items):
            ly = 40 + i * 18
            pygame.draw.rect(screen, color, (legend_x, ly, 12, 12))
            text = font.render(label, True, (180, 180, 180))
            screen.blit(text, (legend_x + 18, ly - 2))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
