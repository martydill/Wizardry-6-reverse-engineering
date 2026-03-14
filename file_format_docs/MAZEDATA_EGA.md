# MAZEDATA.EGA File Format — Wall Texture Tile Atlas

Applies to: `MAZEDATA.EGA` (single file)

## Overview

`MAZEDATA.EGA` is a tile atlas containing **153 wall-texture primitives** used to
assemble the 3D dungeon view. Each tile represents one wall face or wall segment
at a specific rendering distance and position. Tiles vary in size.

The file has three sections: a **file header**, a **display-list table**, and
**sequential planar pixel data**.

## Identification

Detected by: `"MAZEDATA"` in filename (case-insensitive).

## File Layout

```
Offset              Size            Contents
------              ----            --------
0x0000              2               N  = tile count (LE16 = 153)
0x0002              2               N2 = display-list record count (LE16 = 366)
0x0004              N × 5           Tile descriptor table (765 bytes)
0x0301              N2 × 5          Display-list table (1830 bytes)
0x0A27              variable        Sequential planar pixel data
```

For the shipped file:
- Tile descriptor table: `4 + 153×5 = 769` bytes → ends at `0x0300`
- Display-list table: `153×5 + 366×5 = 2595` bytes → ends at `0x0A26`
- Pixel data starts at: `4 + 153×5 + 366×5 = 0x0A27`

> **Common mistake**: pixel data does NOT start at `0x0800`. The display-list table
> continues from `0x0301` to `0x0A26` — skipping it produces garbled tiles.

## Section 1: Tile Descriptor Table (N × 5 bytes)

One 5-byte descriptor per tile, starting at offset `0x0004`:

```
Byte  Field       Description
----  -----       -----------
0–1   seg         LE16 segment value
2     b2          Byte sub-offset within segment (values: 0, 4, 8, or 12)
3     w_units     Width in 8-pixel units (pixel width = w_units × 8)
4     height      Height in pixels
```

The tile's byte offset from the start of pixel data is:

```
abs_off  = seg × 16 + b2
file_off = PIXEL_DATA_OFFSET + abs_off   (= 0x0A27 + abs_off)
```

Tile byte length:

```
tile_bytes = 4 × w_units × height
```

Tiles where `w_units == 0` or `height == 0` are empty/placeholder entries.

## Section 2: Display-List Table (N2 × 5 bytes)

Each record describes one draw call for compositing tiles into the dungeon view.
Each 5-byte entry consists of a **4-byte record** followed by a **1-byte zero separator**:

```
Byte  Field           Description
----  -----           -----------
0     b0              Record type / control byte
1     tile_id         1-indexed tile ID (tile_id - 1 = index into descriptor table)
2     x_bytes         X position in byte units (multiply by 8 for pixels)
3     y_pixels        Y position in pixels
4     (zero)          Group separator (always 0x00)
```

Groups of consecutive records (separated by zero bytes) form composite sprites —
multiple tiles drawn together make up one complete wall face at a given depth.

The display-list table is not used by the tile decoder; it is used by the dungeon
renderer to know which tiles to draw and where.

## Section 3: Pixel Data — Sequential Planar EGA

Pixel data begins at `PIXEL_DATA_OFFSET = 0x0A27`.

Each tile is encoded as **sequential planar EGA**: the 4 bit planes are stored
consecutively, plane 0 through plane 3. Planes are NOT interleaved by row.

```
Tile pixel data layout (for a tile of width W=w_units×8, height H):
  Plane 0:  (W/8) × H bytes   (bit 0 of each pixel's color index)
  Plane 1:  (W/8) × H bytes   (bit 1)
  Plane 2:  (W/8) × H bytes   (bit 2)
  Plane 3:  (W/8) × H bytes   (bit 3)
  Total  =  4 × (W/8) × H  =  4 × w_units × H bytes
```

Within each plane row, **MSB = leftmost pixel** (bit 7 → column 0, bit 0 → column 7).

To reconstruct pixel at `(x, y)` within a tile of width `W`:

```python
bytes_per_row = W // 8
plane_size    = bytes_per_row * H
byte_idx      = y * bytes_per_row + x // 8
bit_mask      = 0x80 >> (x % 8)
color = 0
for plane in range(4):
    if tile_data[plane * plane_size + byte_idx] & bit_mask:
        color |= (1 << plane)
# color is a 4-bit palette index (0–15)
```

## Palette

Uses **`TITLEPAG_PALETTE`** — the custom Wizardry 6 EGA register mapping.
No palette is embedded in the file. No transparency (all 16 indices are opaque).

```
Index 0:  Black        (  0,   0,   0)
Index 1:  White        (255, 255, 255)
Index 2:  Bright Blue  ( 85,  85, 255)
Index 3:  Bright Mag   (255,  85, 255)
Index 4:  Bright Red   (255,  85,  85)
Index 5:  Yellow       (255, 255,  85)
Index 6:  Bright Green ( 85, 255,  85)
Index 7:  Bright Cyan  ( 85, 255, 255)
Index 8:  Dark Gray    ( 85,  85,  85)
Index 9:  Light Gray   (170, 170, 170)
Index 10: Blue         (  0,   0, 170)
Index 11: Magenta      (170,   0, 170)
Index 12: Red          (170,   0,   0)
Index 13: Brown        (170,  85,   0)
Index 14: Green        (  0, 170,   0)
Index 15: Cyan         (  0, 170, 170)
```

## Decoder Reference

`bane/data/sprite_decoder.py` — `decode_mazedata_tiles(path)`:

```python
n  = data[0] | (data[1] << 8)   # 153
n2 = data[2] | (data[3] << 8)   # 366
PIXEL_DATA_OFFSET = 4 + n * 5 + 5 * n2   # = 0x0A27

for i in range(n):
    base    = 4 + i * 5
    seg     = data[base] | (data[base+1] << 8)
    b2      = data[base+2]          # 0, 4, 8, or 12
    w_units = data[base+3]
    height  = data[base+4]
    abs_off  = seg * 16 + b2
    file_off = PIXEL_DATA_OFFSET + abs_off
    width    = w_units * 8
    tile_bytes = 4 * w_units * height
    payload  = data[file_off : file_off + tile_bytes]
    sprite   = EGADecoder(palette=TITLEPAG_PALETTE).decode_planar(
        payload, width=width, height=height, msb_first=True
    )
```

`decode_ega_frames()` routes MAZEDATA to `decode_mazedata_tiles()`, returning all 153
tiles as individual `Sprite` objects (one frame per tile in the viewer).

## Viewer

```
python loaders/ega_viewer.py gamedata/MAZEDATA.EGA
```

Keys: `Left`/`Right`/`Space` = cycle through tiles (153 frames), `Esc` = quit.

Sprite sheet export:

```
python -m loaders.extract_mazedata_tiles
```

Outputs `output/mazedata/spritesheet.png` — all 153 tiles in a labeled grid.
