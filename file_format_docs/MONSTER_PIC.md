# Monster .PIC File Format

Applies to: `MON00.PIC`, `MON01.PIC`, ... `MON11.PIC`, etc.

## Overview

Each `.PIC` file contains one monster's sprite animation as a collection of frames.
The entire file is **RLE-compressed** from byte 0 (no uncompressed header).
After decompression, the data begins with a **frame table header** followed by
**sparse tiled planar pixel data**.

Sprites are individual character-sized images (e.g. 48×68, 64×51 pixels), not full-screen.
Each frame may be a different size.

## Step 1: RLE Decompression

The file is processed in **0x1000-byte (4096-byte) chunks**. Within each chunk, bytes
at indices `0..0x0FFE` (i.e. `i < 0x0FFF`) are processed as control bytes.

### Control byte encoding

| Value       | Meaning                                                   |
|-------------|-----------------------------------------------------------|
| `0x00`      | **End of stream** — stop decompression immediately        |
| `0x01–0x7F` | **Literal run** — copy the next N bytes verbatim          |
| `0x80–0xFF` | **Repeat run** — repeat the next byte `(256 - N)` times  |

Repeat count for `0x80–0xFF`: `count = 256 - ctrl`. For example, `0xFE` repeats the
next byte 2 times; `0x80` repeats it 128 times.

The decompressor never reads past index `0x0FFE` within a chunk (the last byte at
index `0x0FFF` is skipped as a chunk boundary artifact). After consuming a full chunk,
the next 0x1000 bytes are loaded and processing continues until `0x00` is seen.

## Step 2: Decompressed Data Layout

```
Offset         Size            Contents
------         ----            --------
0x0000         2               header_len as LE16 (always 0x0258 = 600)
0x0002         header_len-2    frame records (fills remainder of header)
header_len     variable        sparse tile payload (pixel data for all frames)
```

## Step 3: Frame Table Header

`header_len` is read from the first 2 bytes as a little-endian uint16.
The canonical value is **0x0258 (600 bytes)** = 25 frame record slots × 24 bytes each.

Records where both the offset word and dimension word are zero are skipped (empty slots).
Records where either `width_tiles` or `height_tiles` is zero are also skipped.

### 24-byte Frame Record

```
Offset  Size  Field           Description
------  ----  -----           -----------
0       2     offset          LE16: absolute byte offset into decompressed data
                              where this frame's tile payload begins
2       2     wh              LE16: low byte = width_tiles, high byte = height_tiles
4       20    mask            Bitmask indicating which tiles are present in payload
```

Pixel dimensions:
- `width  = width_tiles  × 8`
- `height = height_tiles × 8`

Both dimensions must be multiples of 8 (the tile size).

### Tile Presence Bitmask (20 bytes)

The 20-byte mask encodes which of the frame's `width_tiles × height_tiles` tiles
are present in the payload. Tiles are indexed **row-major** (left-to-right,
top-to-bottom): tile 0 = top-left, tile 1 = top-right of row 0, etc.

Bit encoding: **LSB-first** within each byte.
- Tile N → byte `N // 8`, bit `N % 8` (i.e. `mask[N//8] & (1 << (N%8))`)

The number of set bits equals the number of 32-byte tile blocks in the payload for
this frame: `payload_byte_len = popcount(mask) × 32`.

## Step 4: Pixel Data — Sparse Tiled Planar

Each frame's pixel data is a **sparse** sequence of 32-byte tile blocks, one for each
tile whose bit is set in the mask, in tile index order (ascending).

**Absent tiles** (bit not set) are filled with `0xFF` bytes before decoding, which
produces palette index 15 (transparent) for all pixels in that tile.

### 32-byte Tile Block (8×8 pixels)

```
Bytes 0–7:   Plane 0  (bit 0 of each pixel's color index)
Bytes 8–15:  Plane 1  (bit 1)
Bytes 16–23: Plane 2  (bit 2)
Bytes 24–31: Plane 3  (bit 3)
```

Each plane is 8 bytes, one byte per row. Within each byte:
- **MSB = leftmost pixel** (bit 7 → column 0, bit 0 → column 7)

To decode pixel at `(col, row)` within a tile:

```python
mask_bit = 0x80 >> col
color = 0
for plane in range(4):
    if tile_bytes[row + plane * 8] & mask_bit:
        color |= (1 << plane)
# color is a 4-bit palette index (0–15); 15 = transparent
```

### Tile Arrangement in the Image

Tiles from the reconstructed full tile array are laid out **row-major**:
- Tile 0 → top-left 8×8 block
- Tile 1 → next 8×8 block to the right
- After `width_tiles` tiles, wrap to the next row

## Palette

Uses **`TITLEPAG_PALETTE`** (the same custom EGA register mapping as full-screen images).
No palette is embedded in the file.

**Palette index 15 is transparent** (rendered as fully transparent when displaying).
Absent tiles decode entirely to index 15 and thus appear transparent.

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
Index 15: Cyan → transparent
```

## Decoder Reference

`bane/data/pic_decoder.py`:

- `_decode_rle(data)` — decompresses the raw file bytes
- `_iter_frame_entries(decompressed, header_size)` — parses the 600-byte frame table
- `decode_pic_frames(data)` — full pipeline: decompress → parse header → decode all frames

```python
decompressed = _decode_rle(raw_bytes)
header_size = struct.unpack("<H", decompressed[:2])[0]  # = 0x0258

for offset, width_tiles, height_tiles, mask in _iter_frame_entries(decompressed, header_size):
    width, height = width_tiles * 8, height_tiles * 8
    set_bits = sum(b.bit_count() for b in mask)
    payload = decompressed[offset : offset + set_bits * 32]

    # Expand sparse payload to full tile array; absent tiles → 0xFF
    full_data = bytearray(b'\xff' * (width_tiles * height_tiles * 32))
    ptr = 0
    for tile_idx in range(width_tiles * height_tiles):
        if mask[tile_idx // 8] & (1 << (tile_idx % 8)):
            full_data[tile_idx*32 : tile_idx*32+32] = payload[ptr : ptr+32]
            ptr += 32

    sprite = EGADecoder(palette=TITLEPAG_PALETTE).decode_tiled_planar(
        bytes(full_data), width, height, msb_first=True
    )
```

## Viewer

```
python -m loaders.pic_viewer .\gamedata\MON11.PIC
```

Keys: `Left`/`Right`/`Space` = cycle animation frames, `Up`/`Down` = switch file, `Esc` = quit.
Palette index 15 is rendered transparent (alpha = 0).
