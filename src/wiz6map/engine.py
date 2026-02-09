from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .data import (
    GameDataBlob,
    PortraitSet,
    RecordData,
    SaveGame,
    load_conversations,
    load_game_data,
    load_items,
    load_monsters,
    load_npcs,
    load_portraits,
    load_save_game,
)
from .loader import MapGrid, MapLoadError, load_map, load_raw_map
from .tiles import TileLoadError, TileSet, load_tiles


@dataclass(frozen=True)
class PlayerState:
    x: int
    y: int


@dataclass(frozen=True)
class GameDataBundle:
    map_grid: MapGrid
    tiles: TileSet | None
    monsters: RecordData | None
    items: RecordData | None
    npcs: RecordData | None
    conversations: RecordData | None
    save_game: SaveGame | None
    portraits: PortraitSet | None
    game_data: GameDataBlob | None


class GameEngine:
    def __init__(self, data: GameDataBundle, player: PlayerState) -> None:
        self._data = data
        self._player = player

    @property
    def player(self) -> PlayerState:
        return self._player

    @property
    def map_grid(self) -> MapGrid:
        return self._data.map_grid

    def move(self, direction: str) -> bool:
        direction = direction.lower()
        dx, dy = 0, 0
        if direction == "n":
            dx, dy = 0, -1
        elif direction == "s":
            dx, dy = 0, 1
        elif direction == "e":
            dx, dy = 1, 0
        elif direction == "w":
            dx, dy = -1, 0
        else:
            raise ValueError("Unknown direction")

        if not self._can_move(dx, dy):
            return False

        self._player = PlayerState(x=self._player.x + dx, y=self._player.y + dy)
        return True

    def _can_move(self, dx: int, dy: int) -> bool:
        next_x = self._player.x + dx
        next_y = self._player.y + dy
        if not (
            0 <= next_x < self.map_grid.width and 0 <= next_y < self.map_grid.height
        ):
            return False

        current = self.map_grid.tile_at(self._player.x, self._player.y)
        if dx == 1 and current.east:
            return False
        if dx == -1 and current.west:
            return False
        if dy == 1 and current.south:
            return False
        if dy == -1 and current.north:
            return False
        return True


def load_game_data_bundle(
    *,
    map_path: str | Path,
    map_format: str | None = None,
    map_width: int | None = None,
    map_height: int | None = None,
    tiles_path: str | Path | None = None,
    tiles_format: str | None = None,
    tile_width: int | None = None,
    tile_height: int | None = None,
    tile_count: int | None = None,
    monsters_path: str | Path | None = None,
    items_path: str | Path | None = None,
    npcs_path: str | Path | None = None,
    conversations_path: str | Path | None = None,
    game_data_path: str | Path | None = None,
    save_game_path: str | Path | None = None,
    save_game_expected_size: int | None = None,
    portraits_path: str | Path | None = None,
    portrait_width: int | None = None,
    portrait_height: int | None = None,
    portrait_count: int | None = None,
) -> GameDataBundle:
    try:
        if map_format == "raw":
            if map_width is None or map_height is None:
                raise MapLoadError("Raw map format requires width and height")
            map_grid = load_raw_map(map_path, width=map_width, height=map_height)
        else:
            map_grid = load_map(map_path, fmt=map_format)
    except MapLoadError as exc:
        raise ValueError(str(exc)) from exc

    tiles = None
    if tiles_path is not None:
        try:
            tiles = load_tiles(
                tiles_path,
                fmt=tiles_format,
                tile_width=tile_width,
                tile_height=tile_height,
                count=tile_count,
            )
        except TileLoadError as exc:
            raise ValueError(str(exc)) from exc

    monsters = load_monsters(monsters_path) if monsters_path else None
    items = load_items(items_path) if items_path else None
    npcs = load_npcs(npcs_path) if npcs_path else None
    conversations = (
        load_conversations(conversations_path) if conversations_path else None
    )
    game_data = load_game_data(game_data_path) if game_data_path else None
    save_game = (
        load_save_game(save_game_path, expected_size=save_game_expected_size)
        if save_game_path
        else None
    )
    portraits = (
        load_portraits(
            portraits_path,
            width=portrait_width,
            height=portrait_height,
            count=portrait_count,
        )
        if portraits_path
        else None
    )

    return GameDataBundle(
        map_grid=map_grid,
        tiles=tiles,
        monsters=monsters,
        items=items,
        npcs=npcs,
        conversations=conversations,
        save_game=save_game,
        portraits=portraits,
        game_data=game_data,
    )
