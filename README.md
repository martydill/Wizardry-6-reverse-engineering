# Wizardry 6 ASCII Map Viewer

This tool loads Wizardry 6 data and renders an ASCII representation of maps. It
also includes a lightweight ASCII game loop that ties together maps, tiles, and
the core data files used by Wizardry 6.

## Supported map formats

1. **W6MP (recommended)**
   * Binary header: `W6MP` (4 bytes)
   * Width: `uint16` little-endian
   * Height: `uint16` little-endian
   * Tile bytes: `width * height` bytes

2. **Raw tile grid**
   * Tile bytes only with no header.
   * Requires `--width` and `--height` when loading.

## Supported tile formats

1. **W6TL (recommended)**
   * Binary header: `W6TL` (4 bytes)
   * Tile width: `uint16` little-endian
   * Tile height: `uint16` little-endian
   * Tile count: `uint16` little-endian
   * Tile bytes: `tile_width * tile_height * tile_count` bytes

2. **Raw tile data**
   * Tile bytes only with no header.
   * Requires tile width/height when loading.

## Tile byte layout

Each map tile byte is interpreted as a bitmask:

| Bit | Meaning |
| --- | ------- |
| 0   | North wall |
| 1   | East wall |
| 2   | South wall |
| 3   | West wall |
| 4   | Door |
| 5   | Secret |
| 6   | Stairs up |
| 7   | Stairs down |

## Usage

```bash
wiz6map path/to/map.w6mp
wiz6map path/to/raw.map --format raw --width 30 --height 30
```

The ASCII output uses `+`, `-`, and `|` for walls and a centered marker for
doors (`D`), secrets (`S`), and stairs (`^`/`v`).

## ASCII game loop

Use `wiz6game` to load Wizardry 6 data files and move a player around the map
with a basic text interface.

```bash
wiz6game path/to/map.w6mp --tiles-path path/to/tiles.w6tl
```

Commands:

- `n`, `s`, `e`, `w` to move.
- `map` to re-render the map with the player marker.
- `quit` to exit.

## Graphical viewer (pygame)

Use `wiz6gfx` to render tiles, portraits, and monster records with pygame.

```bash
wiz6gfx path/to/map.w6mp --tiles-path path/to/tiles.w6tl --portraits-path portraits.w6pt
```

Install pygame via the optional dependency group:

```bash
python -m pip install ".[graphics]"
```

## Supported data formats

The loader supports the original Wizardry 6 containers with headers plus raw
payloads for validation or tooling:

- **Monsters:** `W6MO` header + record size/count + payload.
- **Items:** `W6IT` header + record size/count + payload.
- **NPCs:** `W6NP` header + record size/count + payload.
- **Conversations:** `W6CV` header + record size/count + payload.
- **Game data blob:** `W6GD` header + payload.
- **Save games:** `W6SV` header + payload.
- **Portraits:** `W6PT` header + width/height/count + payload.
