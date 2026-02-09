from __future__ import annotations

from .engine import PlayerState
from .loader import MapGrid


def tile_marker(tile) -> str:
    markers = []
    if tile.door:
        markers.append("D")
    if tile.secret:
        markers.append("S")
    if tile.stairs_up:
        markers.append("^")
    if tile.stairs_down:
        markers.append("v")
    if not markers:
        return "."
    return "".join(markers)[:1]


def render_ascii(grid: MapGrid) -> str:
    lines: list[str] = []
    for y in range(grid.height):
        top = ["+"]
        for x in range(grid.width):
            tile = grid.tile_at(x, y)
            top.append("---" if tile.north else "   ")
            top.append("+")
        lines.append("".join(top))

        middle = []
        for x in range(grid.width):
            tile = grid.tile_at(x, y)
            middle.append("|" if tile.west else " ")
            marker = tile_marker(tile)
            middle.append(f" {marker} ")
        last_tile = grid.tile_at(grid.width - 1, y)
        middle.append("|" if last_tile.east else " ")
        lines.append("".join(middle))

    bottom = ["+"]
    for x in range(grid.width):
        tile = grid.tile_at(x, grid.height - 1)
        bottom.append("---" if tile.south else "   ")
        bottom.append("+")
    lines.append("".join(bottom))
    return "\n".join(lines)


def render_ascii_with_player(grid: MapGrid, player: PlayerState) -> str:
    lines: list[str] = []
    for y in range(grid.height):
        top = ["+"]
        for x in range(grid.width):
            tile = grid.tile_at(x, y)
            top.append("---" if tile.north else "   ")
            top.append("+")
        lines.append("".join(top))

        middle = []
        for x in range(grid.width):
            tile = grid.tile_at(x, y)
            middle.append("|" if tile.west else " ")
            if x == player.x and y == player.y:
                middle.append(" @ ")
            else:
                marker = tile_marker(tile)
                middle.append(f" {marker} ")
        last_tile = grid.tile_at(grid.width - 1, y)
        middle.append("|" if last_tile.east else " ")
        lines.append("".join(middle))

    bottom = ["+"]
    for x in range(grid.width):
        tile = grid.tile_at(x, grid.height - 1)
        bottom.append("---" if tile.south else "   ")
        bottom.append("+")
    lines.append("".join(bottom))
    return "\n".join(lines)
