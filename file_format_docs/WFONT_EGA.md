# Wizardry VI `WFONT*.EGA` Font File Format

## Scope and sources

This document describes the `WFONT` font family used by Wizardry VI as implemented in this repository, primarily from:

- `loaders/render_font.py` (how the fonts are consumed and mapped to text/codes)
- `bane/data/sprite_decoder.py` (`decode_ega_frames` branch for `WFONT` files)

It covers the on-disk structure for:

- `WFONT0.EGA` (monochrome text font)
- `WFONT1.EGA` … `WFONT4.EGA` (4-plane EGA color UI fonts)

---

## Quick reference

- **Glyph count:** 128 glyphs per file.
- **Glyph size:** 8×8 pixels.
- **Two encodings exist:**
  - **1bpp packed rows** (`WFONT0.EGA`, 1024 bytes total)
  - **4-plane EGA planar** (`WFONT1`-`WFONT4`, 4096 bytes total)
- **Indexing model:**
  - `WFONT0`: glyph index `N` corresponds to ASCII code `N`.
  - `WFONT1`-`WFONT4`: glyph index `N` corresponds to an internal game/UI character code `N`.

---

## File naming and semantics

The renderer expects these files under `gamedata/`:

- `WFONT0.EGA`
- `WFONT1.EGA`
- `WFONT2.EGA`
- `WFONT3.EGA`
- `WFONT4.EGA`

`WFONT0` is used for normal text rendering from input strings; the code uppercases text before lookup. `WFONT1`-`WFONT4` are rendered by explicit codepoints (`--chars`) rather than ASCII text.

---

## Common invariants (all WFONT files)

## 1) Glyph grid geometry

Each glyph is fixed-size:

- Width = 8 pixels
- Height = 8 pixels

No per-glyph metadata table is used in these files; glyph `i` is located by fixed-size striding.

## 2) Glyph count

The decoder uses:

- `count = 128`

So glyph indices are expected in `[0, 127]`.

## 3) Palette domain

Decoded pixels are palette indices in a 4-bit domain `[0, 15]` (even for 1bpp, where only 0 and 15 are emitted in current logic).

---

## `WFONT0.EGA` binary layout (1bpp)

## File size

- Exactly **1024 bytes**.
- Formula: `128 glyphs × 8 bytes/glyph = 1024`.

## Per-glyph structure

Each glyph occupies **8 bytes**:

- 1 byte per row
- 8 rows total

Within each row byte, bits are read **MSB to LSB** as left-to-right pixels:

- Bit 7 => x=0
- ...
- Bit 0 => x=7

## Pixel value mapping

For each bit:

- `0` bit => palette index `0` (background)
- `1` bit => palette index `15` (foreground/white)

So this is strictly monochrome in storage; colorization can be applied at render time.

## Byte offset formulas

Given glyph index `g` (0..127), row `r` (0..7):

- `glyph_base = g * 8`
- `row_byte_offset = glyph_base + r`

Pixel at `(x, y)` inside glyph (`x` 0..7, `y` 0..7):

- `b = data[g*8 + y]`
- `bit = (b >> (7 - x)) & 1`
- `pixel = 15 if bit else 0`

---

## `WFONT1.EGA`..`WFONT4.EGA` binary layout (4-plane EGA)

## File size

- Exactly **4096 bytes** each.
- Formula: `128 glyphs × 32 bytes/glyph = 4096`.

## Per-glyph structure

Each glyph occupies **32 bytes**, split into 4 planes:

- Bytes `0..7`: plane 0 (bit 0)
- Bytes `8..15`: plane 1 (bit 1)
- Bytes `16..23`: plane 2 (bit 2)
- Bytes `24..31`: plane 3 (bit 3)

Each plane contributes one bit per pixel for the 8×8 glyph.

## Plane row organization

For each plane, there are 8 row bytes. Inside each row byte, bits are read MSB->LSB for x=0..7.

Given glyph index `g`, row `y`, column `x`:

- `glyph_base = g * 32`
- `plane_byte[p] = data[glyph_base + p*8 + y]` for `p in 0..3`
- `bit_p = (plane_byte[p] >> (7 - x)) & 1`
- `color_index = bit_0 | (bit_1 << 1) | (bit_2 << 2) | (bit_3 << 3)`

Equivalent interpretation:

- plane 0 contributes least-significant bit of the 4-bit color index
- plane 3 contributes most-significant bit

## Byte offset formulas

For glyph `g`, plane `p`, row `r`:

- `glyph_base = g * 32`
- `byte_offset = glyph_base + (p * 8) + r`

---

## Character/code mapping behavior in this codebase

## `WFONT0`

- Intended for ASCII text entry.
- Renderer maps character by `ord(ch)` directly to glyph index.
- Text is transformed to uppercase before rendering.
- Out-of-range codes are skipped.

## `WFONT1`-`WFONT4`

- Intended for game UI symbol codes.
- Renderer expects explicit numeric codes (e.g. `--chars 1,2,3`).
- No ASCII semantics are assumed by default in this path.

---

## Transparency and color usage during rendering

When converted to a `pygame.Surface` in `render_font.py`:

- Palette index `0` is treated as transparent (alpha 0) when requested.
- Other indices are looked up in the sprite palette.

For `WFONT0` specifically:

- Storage uses only indices 0 and 15.
- After blitting, white pixels (`255,255,255`) can be remapped to an arbitrary foreground RGB (`--fg`) via `PixelArray.replace`.
- Background fill is provided by the destination surface (`--bg`) rather than encoded in file.

For `WFONT1`-`WFONT4`:

- 4-bit indices 0..15 are rendered using EGA palette values as-is.

---

## Structural validation heuristics

A practical parser can identify WFONT flavor by file length:

- `len == 1024` => `WFONT0` style (1bpp, 8 bytes/glyph)
- `len == 4096` => `WFONT1-4` style (4-plane, 32 bytes/glyph)
- Other lengths => invalid/unknown for WFONT in current implementation

Recommended checks:

1. Filename contains `WFONT` (current loader gate).
2. File length is exactly 1024 or 4096.
3. Decoded glyph count is 128 and each glyph is 8×8.

---

## Reference pseudocode

```python
# WFONT0 decode
for g in range(128):
    out = [0] * 64
    base = g * 8
    for y in range(8):
        b = data[base + y]
        for x in range(8):
            out[y*8 + x] = 15 if ((b >> (7-x)) & 1) else 0

# WFONT1-4 decode
for g in range(128):
    out = [0] * 64
    base = g * 32
    for y in range(8):
        p0 = data[base + 0*8 + y]
        p1 = data[base + 1*8 + y]
        p2 = data[base + 2*8 + y]
        p3 = data[base + 3*8 + y]
        for x in range(8):
            s = 7 - x
            c = ((p0 >> s) & 1) | (((p1 >> s) & 1) << 1) | (((p2 >> s) & 1) << 2) | (((p3 >> s) & 1) << 3)
            out[y*8 + x] = c
```

---

## Notes / limitations

- This format description reflects the repository's implemented decoding logic.
- It does not currently define any external header/version/footer for WFONT files; decoding is purely size- and naming-driven.
- The meaning of specific glyph codes in `WFONT1`-`WFONT4` (semantic symbol table) is outside this binary format spec and should be documented separately if reverse-mapped from game usage.
