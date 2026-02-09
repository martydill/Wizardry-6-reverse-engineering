# Wizardry 6 ASCII Map Viewer

This tool loads Wizardry 6 map data and renders an ASCII representation.

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
