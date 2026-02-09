"""Map/maze data loader and utilities.

Handles loading dungeon level data from SCENARIO.DBS and provides
utilities for querying tile data, pathfinding, and map analysis.

Map tile encoding (per Wizardry Legacy research):
- Wall byte: 4 walls × 2-bit pairs
  bits 0-1: North wall type (0=none, 1=wall, 2=door, 3=secret)
  bits 2-3: East wall type
  bits 4-5: South wall type
  bits 6-7: West wall type
- Additional bytes for floor/ceiling, specials, encounters, events
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from bane.data.enums import Direction, TileSpecial, WallType
from bane.data.models import DungeonLevel, TileData

logger = logging.getLogger(__name__)


@dataclass
class MapPosition:
    """A position in the dungeon."""

    level: int
    x: int
    y: int
    facing: Direction = Direction.NORTH

    def forward(self) -> MapPosition:
        """Get the position one step forward in the current facing direction."""
        return MapPosition(
            level=self.level,
            x=self.x + self.facing.dx,
            y=self.y + self.facing.dy,
            facing=self.facing,
        )

    def turn_left(self) -> MapPosition:
        return MapPosition(self.level, self.x, self.y, self.facing.turn_left())

    def turn_right(self) -> MapPosition:
        return MapPosition(self.level, self.x, self.y, self.facing.turn_right())

    def turn_around(self) -> MapPosition:
        return MapPosition(self.level, self.x, self.y, self.facing.reverse())


class DungeonMap:
    """Runtime dungeon map manager.

    Provides high-level queries over parsed dungeon level data:
    - Movement validation
    - Line-of-sight for dungeon rendering
    - Special tile lookups
    - Visited tile tracking for automap
    """

    def __init__(self) -> None:
        self._levels: dict[int, DungeonLevel] = {}
        self._visited: dict[int, set[tuple[int, int]]] = {}  # level -> set of (x, y)

    def load_levels(self, levels: dict[int, DungeonLevel]) -> None:
        """Load dungeon levels from parsed scenario data."""
        self._levels = dict(levels)
        logger.info("Loaded %d dungeon levels", len(self._levels))

    def get_level(self, level_id: int) -> DungeonLevel | None:
        return self._levels.get(level_id)

    @property
    def level_ids(self) -> list[int]:
        return sorted(self._levels.keys())

    def get_tile(self, level: int, x: int, y: int) -> TileData | None:
        """Get tile at the specified position."""
        lv = self._levels.get(level)
        if lv is None:
            return None
        return lv.get_tile(x, y)

    def can_move(self, pos: MapPosition) -> bool:
        """Check if movement from pos in pos.facing direction is possible."""
        tile = self.get_tile(pos.level, pos.x, pos.y)
        if tile is None:
            return False

        # Check wall in the movement direction
        wall = tile.get_wall(pos.facing)
        if wall == WallType.WALL or wall == WallType.SECRET:
            return False

        # Also check the destination tile exists
        dest = pos.forward()
        dest_tile = self.get_tile(dest.level, dest.x, dest.y)
        if dest_tile is None:
            return False

        # Check for one-sided walls (the reverse wall from the destination)
        reverse_wall = dest_tile.get_wall(pos.facing.reverse())
        if reverse_wall == WallType.WALL:
            return False

        return True

    def can_see_through(self, pos: MapPosition) -> bool:
        """Check if you can see through the wall in front (for dungeon rendering)."""
        tile = self.get_tile(pos.level, pos.x, pos.y)
        if tile is None:
            return False
        wall = tile.get_wall(pos.facing)
        return wall == WallType.NONE

    def get_special(self, level: int, x: int, y: int) -> TileSpecial:
        """Get the special tile type at a position."""
        tile = self.get_tile(level, x, y)
        if tile is None:
            return TileSpecial.NONE
        return tile.special

    def get_encounter_chance(self, level: int, x: int, y: int) -> int:
        """Get random encounter probability (0-100) at a position."""
        tile = self.get_tile(level, x, y)
        if tile is None:
            return 0
        return tile.encounter_chance

    def mark_visited(self, level: int, x: int, y: int) -> None:
        """Mark a tile as visited for the automap."""
        if level not in self._visited:
            self._visited[level] = set()
        self._visited[level].add((x, y))

    def is_visited(self, level: int, x: int, y: int) -> bool:
        """Check if a tile has been visited."""
        return (x, y) in self._visited.get(level, set())

    def get_visited_tiles(self, level: int) -> set[tuple[int, int]]:
        """Get all visited tiles on a level."""
        return self._visited.get(level, set())

    def get_view_cells(self, pos: MapPosition, max_depth: int = 6) -> list[MapPosition]:
        """Get the list of visible cells from a position for dungeon rendering.

        Returns cells in front-to-back order for the first-person view.
        Stops at walls.
        """
        cells: list[MapPosition] = []
        current = pos
        for _ in range(max_depth):
            if not self.can_see_through(current):
                cells.append(current)  # include the wall cell
                break
            next_pos = current.forward()
            cells.append(current)
            current = MapPosition(
                level=next_pos.level,
                x=next_pos.x,
                y=next_pos.y,
                facing=pos.facing,
            )
        return cells

    def find_special_tiles(
        self, level_id: int, special: TileSpecial
    ) -> list[tuple[int, int]]:
        """Find all tiles of a given special type on a level."""
        lv = self._levels.get(level_id)
        if lv is None:
            return []
        results = []
        for y in range(lv.height):
            for x in range(lv.width):
                tile = lv.tiles[y][x]
                if tile.special == special:
                    results.append((x, y))
        return results

    def get_ascii_map(self, level_id: int) -> str:
        """Generate an ASCII art representation of a dungeon level for debugging."""
        lv = self._levels.get(level_id)
        if lv is None:
            return f"Level {level_id} not loaded"

        # Each tile is 3x3 characters in the ASCII map
        char_w = lv.width * 3 + 1
        char_h = lv.height * 3 + 1
        grid = [[" "] * char_w for _ in range(char_h)]

        for y in range(lv.height):
            for x in range(lv.width):
                tile = lv.tiles[y][x]
                cx = x * 3
                cy = y * 3

                # Draw walls
                wall_chars = {
                    WallType.NONE: " ",
                    WallType.WALL: "#",
                    WallType.DOOR: "+",
                    WallType.SECRET: "?",
                }

                # North wall
                if tile.north_wall != WallType.NONE:
                    ch = wall_chars[tile.north_wall]
                    grid[cy][cx + 1] = ch
                    grid[cy][cx + 2] = ch

                # South wall
                if tile.south_wall != WallType.NONE:
                    ch = wall_chars[tile.south_wall]
                    grid[cy + 3][cx + 1] = ch
                    grid[cy + 3][cx + 2] = ch

                # West wall
                if tile.west_wall != WallType.NONE:
                    ch = wall_chars[tile.west_wall]
                    grid[cy + 1][cx] = ch
                    grid[cy + 2][cx] = ch

                # East wall
                if tile.east_wall != WallType.NONE:
                    ch = wall_chars[tile.east_wall]
                    grid[cy + 1][cx + 3] = ch
                    grid[cy + 2][cx + 3] = ch

                # Corners
                grid[cy][cx] = "+"
                grid[cy][cx + 3] = "+"
                grid[cy + 3][cx] = "+"
                grid[cy + 3][cx + 3] = "+"

                # Tile center content
                special_chars = {
                    TileSpecial.STAIRS_UP: "U",
                    TileSpecial.STAIRS_DOWN: "D",
                    TileSpecial.TELEPORTER: "T",
                    TileSpecial.SPINNER: "S",
                    TileSpecial.DARK_ZONE: "X",
                    TileSpecial.ANTI_MAGIC: "A",
                    TileSpecial.DAMAGE_FLOOR: "!",
                    TileSpecial.PIT: "P",
                    TileSpecial.CHUTE: "C",
                }
                center = special_chars.get(tile.special, ".")
                grid[cy + 1][cx + 1] = center

                if tile.fixed_encounter_id is not None:
                    grid[cy + 1][cx + 2] = "E"
                elif tile.event_id is not None:
                    grid[cy + 1][cx + 2] = "e"

        return "\n".join("".join(row) for row in grid)
