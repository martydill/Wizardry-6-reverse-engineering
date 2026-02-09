from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

W6MP_HEADER = b"W6MP"


class MapLoadError(ValueError):
    """Raised when map data cannot be parsed."""


@dataclass(frozen=True)
class MapTile:
    value: int

    @property
    def north(self) -> bool:
        return bool(self.value & 0b0000_0001)

    @property
    def east(self) -> bool:
        return bool(self.value & 0b0000_0010)

    @property
    def south(self) -> bool:
        return bool(self.value & 0b0000_0100)

    @property
    def west(self) -> bool:
        return bool(self.value & 0b0000_1000)

    @property
    def door(self) -> bool:
        return bool(self.value & 0b0001_0000)

    @property
    def secret(self) -> bool:
        return bool(self.value & 0b0010_0000)

    @property
    def stairs_up(self) -> bool:
        return bool(self.value & 0b0100_0000)

    @property
    def stairs_down(self) -> bool:
        return bool(self.value & 0b1000_0000)


@dataclass(frozen=True)
class MapGrid:
    width: int
    height: int
    tiles: tuple[MapTile, ...]

    def tile_at(self, x: int, y: int) -> MapTile:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError("Tile coordinates out of bounds")
        return self.tiles[y * self.width + x]


@dataclass(frozen=True)
class MapData:
    width: int
    height: int
    tiles: Iterable[int]


def load_map(path: str | Path, *, fmt: str | None = None) -> MapGrid:
    data = Path(path).read_bytes()
    if not data:
        raise MapLoadError("Map file is empty")

    if fmt == "w6mp" or (fmt is None and data.startswith(W6MP_HEADER)):
        return _load_w6mp(data)

    if fmt == "raw":
        raise MapLoadError("Raw format requires explicit width and height")

    if fmt is not None:
        raise MapLoadError(f"Unknown format: {fmt}")

    raise MapLoadError(
        "Unable to detect format. Use --format raw with --width/--height."
    )


def load_raw_map(
    path: str | Path,
    *,
    width: int,
    height: int,
) -> MapGrid:
    data = Path(path).read_bytes()
    if len(data) != width * height:
        raise MapLoadError(
            "Raw map size does not match width * height "
            f"({len(data)} != {width * height})."
        )

    tiles = tuple(MapTile(value) for value in data)
    return MapGrid(width=width, height=height, tiles=tiles)


def _load_w6mp(data: bytes) -> MapGrid:
    if len(data) < 8:
        raise MapLoadError("W6MP header too short")

    width = int.from_bytes(data[4:6], "little")
    height = int.from_bytes(data[6:8], "little")
    if width <= 0 or height <= 0:
        raise MapLoadError("Invalid map dimensions")

    expected = width * height
    payload = data[8:]
    if len(payload) != expected:
        raise MapLoadError(
            f"W6MP payload length {len(payload)} does not match expected {expected}."
        )

    tiles = tuple(MapTile(value) for value in payload)
    return MapGrid(width=width, height=height, tiles=tiles)
