# Full-Screen EGA File Format

Applies to: `TITLEPAG.EGA`, `DRAGONSC.EGA`, `GRAVEYRD.EGA` (and other 32768-byte `.EGA` files)

## Overview

Full-screen EGA images are 320×200 pixels, 16 colors, stored as **sequential planar EGA**
with no file header and no embedded palette. File size is exactly **32768 bytes**.

## Identification

Detected by: `len(data) == 32768`

## File Layout

The file is divided into 4 equal **8192-byte plane slots**, one per EGA bit plane:

```
Offset        Size    Contents
------        ----    --------
0x0000        8192    Plane 0 slot  (bit 0 of each pixel's color index)
0x2000        8192    Plane 1 slot  (bit 1)
0x4000        8192    Plane 2 slot  (bit 2)
0x6000        8192    Plane 3 slot  (bit 3)
```

Each plane slot holds **8000 bytes of pixel data** followed by **192 bytes of unused padding**:

```
Within each 8192-byte slot:
  Bytes 0–7999:   pixel bitplane data (320×200 / 8 = 8000 bytes)
  Bytes 8000–8191: padding (ignored)
```

## Pixel Encoding

Format: **sequential planar**, MSB-first.

Each plane stores one bit per pixel, packed 8 pixels per byte, MSB = leftmost pixel:

```
Byte layout within a plane row (320 pixels = 40 bytes):
  Byte 0:  pixels 0–7   (bit 7 = pixel 0, bit 0 = pixel 7)
  Byte 1:  pixels 8–15
  ...
  Byte 39: pixels 312–319
```

To reconstruct a pixel at `(x, y)`:

```python
byte_idx = y * 40 + x // 8
bit_mask = 0x80 >> (x % 8)
color = 0
for plane in range(4):
    plane_offset = plane * 8192
    if data[plane_offset + byte_idx] & bit_mask:
        color |= (1 << plane)
# color is a 4-bit EGA palette index (0–15)
```

Plane order is natural `[0, 1, 2, 3]` — plane 0 slot contributes bit 0, plane 3 slot
contributes bit 3 (most significant).

## Palette

Uses **`TITLEPAG_PALETTE`** — a custom Wizardry 6 EGA register mapping. **No palette is
embedded in the file.** The standard EGA default palette does NOT produce correct colors;
this custom mapping must be used.

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

Key non-obvious mappings: index 1 = White (not Blue), index 8 = Dark Gray, index 9 = Light
Gray, index 12 = Red (not Light Red). This differs from standard IBM EGA color ordering.

## Decoder Reference

`bane/data/sprite_decoder.py` — `decode_ega_file()` (32768-byte branch):

```python
decoder = EGADecoder(palette=TITLEPAG_PALETTE)
width, height = 320, 200
bytes_per_plane = 8000  # width * height // 8

image_data = bytearray()
for plane in range(4):
    plane_start = plane * 8192
    image_data.extend(data[plane_start : plane_start + bytes_per_plane])

sprite = decoder.decode_planar(
    bytes(image_data),
    width=320,
    height=200,
    planes=4,
    msb_first=True,
    plane_order=[0, 1, 2, 3],
)
```

`decode_planar()` receives the 32000-byte image_data (4 × 8000 bytes, padding stripped)
as a single sequential planar buffer.

## Viewer

```
python loaders/ega_viewer.py .\gamedata\TITLEPAG.EGA
```

Keys: `Esc` = quit. No frame navigation (single image per file).
