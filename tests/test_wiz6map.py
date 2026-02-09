import tempfile
import unittest
from pathlib import Path

from wiz6map.loader import MapLoadError, load_map, load_raw_map
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


if __name__ == "__main__":
    unittest.main()
