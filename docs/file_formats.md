# Wizardry 6 EGA Graphics Formats

This document describes the binary formats used for various EGA graphics files in Wizardry 6: Bane of the Cosmic Forge.

## 1. Full-Screen Images (TITLEPAG.EGA, etc.)

These files are used for title screens, cutscenes, and special backgrounds.

- **File Size**: 32,768 bytes
- **Resolution**: 320×200 pixels
- **Palette**: 768-byte VGA palette header at the start.
  - 256 entries × 3 bytes (R, G, B).
  - Each component is 6-bit (0–63). Convert to 8-bit by multiplying by 4.
  - Only the first 16 entries are used for EGA rendering.
- **Image Data**: 32,000 bytes starting at offset 768.
- **Format**: **Sequential Planar**.
  - 4 bit planes, each 8,000 bytes (320 × 200 / 8).
  - Planes are stored one after another: Plane 0, then Plane 1, then Plane 2, then Plane 3.
  - **Plane Order**: `[3, 0, 2, 1]` (found via reverse engineering).
  - **Bit Direction**: MSB-first (bit 7 is the leftmost pixel).

## 2. Character Portraits (WPORT*.EGA)

These files contain the small portraits used in the party roster.

- **File Size**: 4,096 bytes
- **Portraits per File**: 14
- **Portrait Dimensions**: 24×24 pixels
- **Format**: **Tiled Planar**.
  - Each portrait is 288 bytes (9 tiles of 8×8 pixels).
  - Tiles are stored in **Row-Major** order (left-to-right, then top-to-bottom).
  - Each 32-byte tile consists of 4 planes (8 bytes per plane):
    - Bytes 0–7: Plane 0 (Blue)
    - Bytes 8–15: Plane 1 (Green)
    - Bytes 16–23: Plane 2 (Red)
    - Bytes 24–31: Plane 3 (Intensity)
- **Palette**: Uses the default 16-color EGA palette.
- **Leftover Space**: 64 bytes at the end of the file (likely padding or metadata).

## 3. Font Collections (WFONT*.EGA)

These files contain monochrome bitmapped fonts.

- **Formats**:
  - **WFONT0.EGA**: 1,024 bytes (128 characters of 8×8 pixels).
  - **WFONT1.EGA** (and others): 4,096 bytes (256 characters of 8×16 pixels).
- **Storage**: Raw 1bpp bitstream.
  - 8 pixels per byte.
  - MSB-first.
  - Characters are stored sequentially.

## 4. Texture Atlas (MAZEDATA.EGA)

Contains all dungeon wall, floor, and ceiling textures.

- **File Size**: 102,303 bytes
- **Primary Atlas**: First 32,000 bytes.
- **Resolution**: 320×200 pixels.
- **Format**: **Sequential Planar** (same as Title screens).
- **Palette**: No header; uses the default 16-color EGA palette.
- **Additional Data**: Remaining 70KB contains additional textures or animation frames.

## 5. Monster Sprites (*.PIC)

Monster sprites are stored in RLE-compressed files.

- **Compression**: High-bit RLE.
  - `0x00`: Terminator.
  - `0x01–0x7F`: Copy the next N bytes literally.
  - `0x80–0xFF`: Repeat the next byte (256 - value) times.
- **Header**: First 2 bytes (LE16) define the header length (typically 600 bytes).
- **Metadata**: Contains a frame table with offsets and sparse tile masks.
- **Format**: **Tiled Planar**.
  - Reconstructs a sparse grid of 8×8 tiles.
  - Uses the same 32-byte tile structure as WPORT files.
