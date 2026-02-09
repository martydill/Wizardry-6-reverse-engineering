import tempfile
import unittest
from pathlib import Path

from wiz6map.combat import CombatState, Monster, PartyMember
from wiz6map.data import GameDataLoadError, load_items, load_monsters, load_save_game
from wiz6map.engine import GameDataBundle, GameEngine, PlayerState
from wiz6map.loader import MapLoadError, MapGrid, MapTile, load_map, load_raw_map
from wiz6map.pygame_viewer import _pixels_from_bytes, _split_monster_frames
from wiz6map.renderer import render_ascii
from wiz6map.tiles import TileLoadError, load_tiles


class TestWizardryMap(unittest.TestCase):
    def test_load_w6mp_and_render(self):
        tiles = bytes([15, 31, 79, 143])
        data = b"W6MP" + (2).to_bytes(2, "little") + (2).to_bytes(2, "little") + tiles
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.w6mp"
            path.write_bytes(data)

            grid = load_map(path)
            ascii_map = render_ascii(grid)

        expected = "\n".join(
            [
                "+---+---+",
                "| . | D |",
                "+---+---+",
                "| ^ | v |",
                "+---+---+",
            ]
        )
        self.assertEqual(ascii_map, expected)

    def test_raw_map_size_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.raw"
            path.write_bytes(bytes([0, 1, 2]))

            with self.assertRaises(MapLoadError):
                load_raw_map(path, width=2, height=2)

    def test_load_w6tl_tiles(self):
        tile_width = 2
        tile_height = 2
        count = 2
        tiles = bytes([0, 1, 2, 3, 4, 5, 6, 7])
        data = (
            b"W6TL"
            + tile_width.to_bytes(2, "little")
            + tile_height.to_bytes(2, "little")
            + count.to_bytes(2, "little")
            + tiles
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.w6tl"
            path.write_bytes(data)

            tile_set = load_tiles(path)

        self.assertEqual(tile_set.tile_width, tile_width)
        self.assertEqual(tile_set.tile_height, tile_height)
        self.assertEqual(len(tile_set.tiles), count)
        self.assertEqual(tile_set.tile_at(1), bytes([4, 5, 6, 7]))

    def test_raw_tile_count_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.tiles"
            path.write_bytes(bytes([0, 1, 2, 3, 4]))

            with self.assertRaises(TileLoadError):
                load_tiles(path, fmt="raw", tile_width=2, tile_height=2, count=2)


class TestWizardryData(unittest.TestCase):
    def test_load_w6mo_records(self):
        record_size = 3
        record_count = 2
        records = bytes([1, 2, 3, 4, 5, 6])
        data = (
            b"W6MO"
            + record_size.to_bytes(2, "little")
            + record_count.to_bytes(2, "little")
            + records
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "monsters.w6mo"
            path.write_bytes(data)

            monsters = load_monsters(path)

        self.assertEqual(monsters.record_size, record_size)
        self.assertEqual(monsters.record_count, record_count)
        self.assertEqual(monsters.record_at(1), bytes([4, 5, 6]))

    def test_load_items_payload_mismatch(self):
        data = (
            b"W6IT"
            + (2).to_bytes(2, "little")
            + (2).to_bytes(2, "little")
            + bytes([1, 2, 3])
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "items.w6it"
            path.write_bytes(data)

            with self.assertRaises(GameDataLoadError):
                load_items(path)

    def test_save_game_expected_size(self):
        data = b"W6SV" + bytes([1, 2, 3])
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "save.w6sv"
            path.write_bytes(data)

            with self.assertRaises(GameDataLoadError):
                load_save_game(path, expected_size=2)


class TestWizardryEngine(unittest.TestCase):
    def test_engine_blocks_walls(self):
        tiles = (
            MapTile(0b0000_0010),
            MapTile(0),
            MapTile(0),
            MapTile(0),
        )
        grid = MapGrid(width=2, height=2, tiles=tiles)
        engine = GameEngine(
            data=GameDataBundle(
                map_grid=grid,
                tiles=None,
                monsters=None,
                items=None,
                npcs=None,
                conversations=None,
                save_game=None,
                portraits=None,
                game_data=None,
            ),
            player=PlayerState(x=0, y=0),
        )

        self.assertFalse(engine.move("e"))
        self.assertTrue(engine.move("s"))


class TestPygameViewerHelpers(unittest.TestCase):
    def test_pixels_from_bytes_pads(self):
        pixels = _pixels_from_bytes(bytes([1, 2, 3]), width=2, height=2)
        self.assertEqual(pixels, ((1, 2), (3, 0)))

    def test_split_monster_frames(self):
        payload = bytes([1, 2, 3, 4, 5, 6, 7, 8])
        first, second = _split_monster_frames(payload, width=2, height=2)
        self.assertEqual(first, ((1, 2), (3, 4)))
        self.assertEqual(second, ((5, 6), (7, 8)))


class TestCombatState(unittest.TestCase):
    def test_combat_resolves_turns(self):
        party = [PartyMember(name="Hero", hp=10, attack=6, defense=1)]
        monsters = [Monster(name="Rat", hp=4, attack=2, defense=0)]
        state = CombatState(party=party, monsters=monsters)

        result = state.perform_attack()
        self.assertIsNotNone(result)
        self.assertEqual(monsters[0].hp, 0)
        self.assertEqual(state.victors, "party")


if __name__ == "__main__":
    unittest.main()
