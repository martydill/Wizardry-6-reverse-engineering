from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

W6TL_HEADER = b"W6TL"


class TileLoadError(ValueError):
    """Raised when tile data cannot be parsed."""


@dataclass(frozen=True)
class TileSet:
    tile_width: int
    tile_height: int
    tiles: tuple[bytes, ...]

    def tile_at(self, index: int) -> bytes:
        if not (0 <= index < len(self.tiles)):
            raise IndexError("Tile index out of bounds")
        return self.tiles[index]

    def tile_pixels(self, index: int) -> tuple[tuple[int, ...], ...]:
        tile = self.tile_at(index)
        pixels = []
        tile_size = self.tile_width * self.tile_height
        if len(tile) != tile_size:
            raise TileLoadError("Tile payload has unexpected length")
        for row in range(self.tile_height):
            start = row * self.tile_width
            end = start + self.tile_width
            pixels.append(tuple(tile[start:end]))
        return tuple(pixels)


def load_tiles(
    path: str | Path,
    *,
    fmt: str | None = None,
    tile_width: int | None = None,
    tile_height: int | None = None,
    count: int | None = None,
) -> TileSet:
    data = Path(path).read_bytes()
    if not data:
        raise TileLoadError("Tile file is empty")

    if fmt == "w6tl" or (fmt is None and data.startswith(W6TL_HEADER)):
        return _load_w6tl(data)

    if fmt == "raw":
        return _load_raw_tiles(
            data, tile_width=tile_width, tile_height=tile_height, count=count
        )

    if fmt is not None:
        raise TileLoadError(f"Unknown format: {fmt}")

    raise TileLoadError(
        "Unable to detect format. Use --format raw with --tile-width/--tile-height."
    )


def _load_w6tl(data: bytes) -> TileSet:
    if len(data) < 10:
        raise TileLoadError("W6TL header too short")

    tile_width = int.from_bytes(data[4:6], "little")
    tile_height = int.from_bytes(data[6:8], "little")
    count = int.from_bytes(data[8:10], "little")
    if tile_width <= 0 or tile_height <= 0 or count <= 0:
        raise TileLoadError("Invalid tile dimensions or count")

    tile_size = tile_width * tile_height
    expected = tile_size * count
    payload = data[10:]
    if len(payload) != expected:
        raise TileLoadError(
            f"W6TL payload length {len(payload)} does not match expected {expected}."
        )

    tiles = tuple(
        payload[index : index + tile_size] for index in range(0, expected, tile_size)
    )
    return TileSet(tile_width=tile_width, tile_height=tile_height, tiles=tiles)


def _load_raw_tiles(
    data: bytes,
    *,
    tile_width: int | None,
    tile_height: int | None,
    count: int | None,
) -> TileSet:
    if tile_width is None or tile_height is None:
        raise TileLoadError("Raw format requires tile_width and tile_height")
    if tile_width <= 0 or tile_height <= 0:
        raise TileLoadError("Invalid tile dimensions")

    tile_size = tile_width * tile_height
    if count is None:
        if len(data) % tile_size != 0:
            raise TileLoadError("Raw tile data length is not divisible by tile size")
        count = len(data) // tile_size
    if count <= 0:
        raise TileLoadError("Invalid tile count")

    expected = tile_size * count
    if len(data) != expected:
        raise TileLoadError(
            f"Raw tile data length {len(data)} does not match expected {expected}."
        )

    tiles = tuple(
        data[index : index + tile_size] for index in range(0, expected, tile_size)
    )
    return TileSet(tile_width=tile_width, tile_height=tile_height, tiles=tiles)
