"""Tests for the map/dungeon system."""

from bane.data.enums import Direction, TileSpecial, WallType
from bane.data.map_loader import DungeonMap, MapPosition
from bane.data.models import DungeonLevel, TileData


def make_test_level(width: int = 4, height: int = 4) -> DungeonLevel:
    """Create a simple test dungeon level."""
    level = DungeonLevel(level_id=0, name="Test", width=width, height=height)
    level.tiles = []
    for y in range(height):
        row = []
        for x in range(width):
            tile = TileData(x=x, y=y)
            # Outer walls
            if y == 0:
                tile.north_wall = WallType.WALL
            if y == height - 1:
                tile.south_wall = WallType.WALL
            if x == 0:
                tile.west_wall = WallType.WALL
            if x == width - 1:
                tile.east_wall = WallType.WALL
            row.append(tile)
        level.tiles.append(row)
    return level


class TestMapPosition:
    def test_forward_north(self):
        pos = MapPosition(0, 5, 5, Direction.NORTH)
        fwd = pos.forward()
        assert fwd.x == 5
        assert fwd.y == 4

    def test_forward_east(self):
        pos = MapPosition(0, 5, 5, Direction.EAST)
        fwd = pos.forward()
        assert fwd.x == 6
        assert fwd.y == 5

    def test_turn_left_and_right(self):
        pos = MapPosition(0, 0, 0, Direction.NORTH)
        left = pos.turn_left()
        assert left.facing == Direction.WEST
        right = pos.turn_right()
        assert right.facing == Direction.EAST

    def test_turn_around(self):
        pos = MapPosition(0, 0, 0, Direction.NORTH)
        back = pos.turn_around()
        assert back.facing == Direction.SOUTH


class TestDungeonMap:
    def setup_method(self):
        self.dungeon = DungeonMap()
        self.level = make_test_level(4, 4)
        self.dungeon.load_levels({0: self.level})

    def test_get_tile(self):
        tile = self.dungeon.get_tile(0, 1, 1)
        assert tile is not None
        assert tile.x == 1
        assert tile.y == 1

    def test_get_tile_out_of_bounds(self):
        assert self.dungeon.get_tile(0, -1, 0) is None
        assert self.dungeon.get_tile(0, 100, 0) is None
        assert self.dungeon.get_tile(99, 0, 0) is None  # wrong level

    def test_can_move_open(self):
        # Interior tiles should allow movement
        pos = MapPosition(0, 1, 1, Direction.EAST)
        assert self.dungeon.can_move(pos)

    def test_cannot_move_through_wall(self):
        # Northern boundary wall
        pos = MapPosition(0, 1, 0, Direction.NORTH)
        assert not self.dungeon.can_move(pos)

    def test_can_move_through_door(self):
        # Add a door
        self.level.tiles[1][1].east_wall = WallType.DOOR
        self.level.tiles[1][2].west_wall = WallType.DOOR
        pos = MapPosition(0, 1, 1, Direction.EAST)
        assert self.dungeon.can_move(pos)

    def test_cannot_move_through_secret_door(self):
        self.level.tiles[1][1].east_wall = WallType.SECRET
        self.level.tiles[1][2].west_wall = WallType.SECRET
        pos = MapPosition(0, 1, 1, Direction.EAST)
        assert not self.dungeon.can_move(pos)

    def test_visited_tiles(self):
        assert not self.dungeon.is_visited(0, 1, 1)
        self.dungeon.mark_visited(0, 1, 1)
        assert self.dungeon.is_visited(0, 1, 1)
        assert not self.dungeon.is_visited(0, 2, 2)

    def test_get_visited_tiles(self):
        self.dungeon.mark_visited(0, 1, 1)
        self.dungeon.mark_visited(0, 2, 2)
        visited = self.dungeon.get_visited_tiles(0)
        assert (1, 1) in visited
        assert (2, 2) in visited

    def test_get_special(self):
        self.level.tiles[2][2].special = TileSpecial.STAIRS_DOWN
        assert self.dungeon.get_special(0, 2, 2) == TileSpecial.STAIRS_DOWN

    def test_find_special_tiles(self):
        self.level.tiles[1][1].special = TileSpecial.STAIRS_UP
        self.level.tiles[3][3].special = TileSpecial.STAIRS_UP
        results = self.dungeon.find_special_tiles(0, TileSpecial.STAIRS_UP)
        assert len(results) == 2
        assert (1, 1) in results
        assert (3, 3) in results

    def test_get_view_cells(self):
        pos = MapPosition(0, 1, 1, Direction.EAST)
        cells = self.dungeon.get_view_cells(pos, max_depth=3)
        assert len(cells) > 0

    def test_ascii_map(self):
        ascii_map = self.dungeon.get_ascii_map(0)
        assert isinstance(ascii_map, str)
        assert "#" in ascii_map  # should have wall characters

    def test_level_ids(self):
        assert self.dungeon.level_ids == [0]
