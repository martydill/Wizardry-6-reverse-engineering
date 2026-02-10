# Wizardry 6 EGA Format Discovery Summary

## Critical Finding: Sequential Planar, Not Row-Interleaved!

After extensive testing and debugging, the correct EGA format for Wizardry 6 files is **sequential planar**, not row-interleaved.

## Format Details

### Sequential Planar Layout
Each bit plane is stored completely before the next plane:

```
Plane 0 (bit 0 of color): 8,000 bytes (for 320×200)
Plane 1 (bit 1 of color): 8,000 bytes
Plane 2 (bit 2 of color): 8,000 bytes
Plane 3 (bit 3 of color): 8,000 bytes
Total: 32,000 bytes
```

Within each plane:
- Pixels stored row by row
- 8 pixels per byte (1 bit per pixel)
- **MSB-first ordering**: bit 7 = leftmost pixel, bit 0 = rightmost pixel

### File Structures

#### MAZEDATA.EGA (Texture Atlas)
```
Offset    Size       Content
0         32,000     Main 320×200 texture atlas (sequential planar)
32,000    70,303     Additional texture data
Total: 102,303 bytes
```

**Important**: NO palette header! Uses DEFAULT_16_PALETTE.

#### Other .EGA Files (TITLEPAG, DRAGONSC, GRAVEYRD)
```
Offset    Size       Content
0         768        VGA palette (256 colors × 3 bytes RGB, only first 16 used)
768       32,000     320×200 image (sequential planar)
Total: 32,768 bytes
```

### VGA Palette Format
- 256 entries × 3 bytes (R, G, B)
- Each component: 0-63 range (6-bit VGA)
- Scale to 8-bit RGB: `value * 4` (clamped to 255)
- Only first 16 entries used for EGA

## Decoder Implementation

### Correct Code
```python
from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE

# MAZEDATA.EGA (no palette header)
decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
atlas = decoder.decode_planar(
    data[:32000],
    width=320,
    height=200,
    msb_first=True
)

# TITLEPAG.EGA etc. (with palette header)
palette = []
for i in range(16):
    r = min(255, data[i * 3] * 4)
    g = min(255, data[i * 3 + 1] * 4)
    b = min(255, data[i * 3 + 2] * 4)
    palette.append((r, g, b))

decoder = EGADecoder(palette=palette)
image = decoder.decode_planar(
    data[768:],  # Skip palette header
    width=320,
    height=200,
    msb_first=True
)
```

## What Was Wrong Initially

### Incorrect Assumptions
1. ❌ Assumed row-interleaved planar format
2. ❌ Thought MAZEDATA.EGA had an index structure
3. ❌ Believed all .EGA files had same structure

### What Actually Works
1. ✅ Sequential planar format for all .EGA files
2. ✅ MAZEDATA.EGA is simply a texture atlas image (no index)
3. ✅ MAZEDATA has no palette header, others do

## Testing Results

### MAZEDATA.EGA
- ✅ Decodes correctly as 320×200 texture atlas
- ✅ Shows horizontal rows of wall/floor/ceiling textures
- ✅ Clear, recognizable texture patterns visible

### TITLEPAG.EGA
- ✅ Decodes correctly with palette header
- ✅ "BANE OF THE COSMIC FORGE" title clearly readable
- ✅ Image structure matches expected title screen

### DRAGONSC.EGA & GRAVEYRD.EGA
- ✅ Both decode successfully with same format

## Tools Created

### `tools/mazedata_decoder.py`
Complete decoder for all .EGA files:
- Handles MAZEDATA.EGA (no palette)
- Handles other .EGA files (with palette)
- Outputs PNG images
- Reports file statistics

### Updated `bane/data/sprite_decoder.py`
- Fixed docstrings to clarify sequential planar format
- Confirmed `decode_planar()` works correctly
- Distinguished from `decode_planar_row_interleaved()` which is for .PIC files

## Next Steps

1. ✅ Format fully understood and documented
2. ✅ Working decoder implemented
3. ⏳ Map texture coordinates within MAZEDATA.EGA atlas
4. ⏳ Analyze remaining 70KB of MAZEDATA.EGA
5. ⏳ Determine how game references textures by ID

## References

- MAZEDATA_FORMAT.md - Complete format specification
- tools/mazedata_decoder.py - Working decoder utility
- Memory updated with correct format information
