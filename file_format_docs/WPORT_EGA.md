# WPORT*.EGA File Format — Character Portraits

Applies to: `WPORT0.EGA`, `WPORT1.EGA`

## Overview

Each WPORT*.EGA file is a collection of **14 character portrait frames**, all 24×24 pixels,
stored sequentially with no file header. Total file size is exactly **4096 bytes**
(14 frames × 288 bytes = 4032 bytes of portrait data + 64 bytes padding at end).

## Identification

Detected by: `len(data) == 4096` AND `"WPORT"` in filename (case-insensitive).

## File Layout

```
Offset       Size     Contents
------       ----     --------
0x000        288      Frame 0  (portrait index 0)
0x120        288      Frame 1
0x240        288      Frame 2
...
0xD80        288      Frame 13
0xFA0–0xFFF   64      Unused padding (zeros)
```

Frame N starts at byte offset `N × 288`.

## Frame Encoding: 24×24 Tiled Planar EGA

Each 288-byte frame encodes a 24×24 pixel image using **tiled planar** format.

### Tile Layout

A 24×24 image = **9 tiles** arranged in a 3×3 grid:

```
Tile 0  Tile 1  Tile 2     (top row)
Tile 3  Tile 4  Tile 5     (middle row)
Tile 6  Tile 7  Tile 8     (bottom row)
```

Tiles are stored **row-major** (left-to-right, then top-to-bottom):
tile 0 = top-left, tile 1 = top-center, tile 2 = top-right, tile 3 = middle-left, etc.

9 tiles × 32 bytes/tile = **288 bytes per frame**.

### Tile Encoding (32 bytes per 8×8 tile)

```
Bytes 0–7:   Plane 0  (bit 0 of each pixel's color index)
Bytes 8–15:  Plane 1  (bit 1)
Bytes 16–23: Plane 2  (bit 2)
Bytes 24–31: Plane 3  (bit 3)
```

Each plane stores 8 rows × 1 byte per row = 8 bytes. Within each byte:
- **MSB = leftmost pixel** (bit 7 → column 0, bit 0 → column 7)

To reconstruct a pixel at `(col, row)` within a tile:

```python
mask = 0x80 >> col
color = 0
for plane in range(4):
    if tile_bytes[row + plane * 8] & mask:
        color |= (1 << plane)
# color is now a 4-bit EGA palette index (0–15)
```

## Palette

Uses **`TITLEPAG_PALETTE`** — the custom Wizardry 6 EGA register mapping. No palette is
embedded in the file.

```
Index 0:  Black       (  0,   0,   0)
Index 1:  White       (255, 255, 255)
Index 2:  Bright Blue ( 85,  85, 255)
Index 3:  Bright Mag  (255,  85, 255)
Index 4:  Bright Red  (255,  85,  85)
Index 5:  Yellow      (255, 255,  85)
Index 6:  Bright Grn  ( 85, 255,  85)
Index 7:  Bright Cyan ( 85, 255, 255)
Index 8:  Dark Gray   ( 85,  85,  85)
Index 9:  Light Gray  (170, 170, 170)
Index 10: Blue        (  0,   0, 170)
Index 11: Magenta     (170,   0, 170)
Index 12: Red         (170,   0,   0)
Index 13: Brown       (170,  85,   0)
Index 14: Green       (  0, 170,   0)
Index 15: Cyan        (  0, 170, 170)
```

No transparency — all 16 palette indices are opaque (unlike monster `.PIC` files where
index 15 is treated as transparent).

## Decoder Reference

`bane/data/sprite_decoder.py` — `decode_ega_frames()` (WPORT branch):

```python
decoder = EGADecoder(palette=list(TITLEPAG_PALETTE))
for i in range(14):
    offset = i * 288
    frame = decoder.decode_tiled_planar(
        data[offset : offset + 288],
        width=24,
        height=24,
    )
```

`decode_tiled_planar()` parameters used:
- `width=24, height=24` — fixed for all WPORT files
- `plane_order=[0,1,2,3]` — default, planes in natural order
- `msb_first=True` — default
- `row_major=True` — default, tiles proceed left-to-right then top-to-bottom

## Viewer

```
python -m loaders.pic_viewer .\gamedata\WPORT1.EGA
```

Keys: `Left`/`Right`/`Space` = cycle frames, `Up`/`Down` = switch to sibling file, `Esc` = quit.
