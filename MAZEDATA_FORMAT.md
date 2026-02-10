# MAZEDATA.EGA File Format

## Overview
MAZEDATA.EGA contains all wall, floor, and ceiling textures for Wizardry 6's dungeon renderer.

## File Format
- **Type**: EGA texture atlas image
- **Dimensions**: 320×200 pixels (first image)
- **Color**: 16 colors (default EGA palette)
- **Storage**: Sequential planar format
- **Size**: 102,303 bytes total (32,000 bytes main atlas + 70,303 bytes additional data)

## Structure

### Image Data (bytes 0-31,999)
The first 32,000 bytes contain a 320×200 EGA image in **sequential planar format**:

```
Sequential planar layout:
- Plane 0 (bit 0): 8,000 bytes (320×200/8)
- Plane 1 (bit 1): 8,000 bytes
- Plane 2 (bit 2): 8,000 bytes
- Plane 3 (bit 3): 8,000 bytes
Total: 32,000 bytes

Each plane stores all pixels for that bit position before moving to the next plane.
```

### Additional Data (bytes 32,000-102,302)
The remaining 70,303 bytes likely contains additional textures, animation frames, or alternate texture sets.

## Important: No Palette Header!
Unlike other .EGA files (TITLEPAG.EGA, DRAGONSC.EGA, GRAVEYRD.EGA), **MAZEDATA.EGA has NO 768-byte palette header**. It uses the default 16-color EGA palette.

## Image Content
The 320×200 texture atlas shows horizontal rows of textures:
- **Stone/brick wall textures** in various styles
- **Floor textures**
- **Ceiling textures**
- **Door textures**
- **Special wall types** (darkness, magical barriers, etc.)

Textures appear to be arranged as horizontal bands in the atlas.

## Decoding

### Python Example
```python
from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE
from PIL import Image

# Read file
with open("MAZEDATA.EGA", "rb") as f:
    data = f.read()

# IMPORTANT: Use DEFAULT_16_PALETTE (no palette header in this file!)
decoder = EGADecoder(palette=DEFAULT_16_PALETTE)

# Decode using SEQUENTIAL planar format (not row-interleaved!)
atlas = decoder.decode_planar(
    data[:32000],
    width=320,
    height=200,
    msb_first=True
)

# Save as PNG
img = Image.frombytes("RGB", (atlas.width, atlas.height), atlas.to_rgb_bytes())
img.save("mazedata_atlas.png")
```

### Decoding Other .EGA Files (TITLEPAG, DRAGONSC, GRAVEYRD)
These files HAVE a 768-byte palette header:

```python
# Read file
with open("TITLEPAG.EGA", "rb") as f:
    data = f.read()

# Extract palette from first 768 bytes (VGA palette format, 0-63 range)
palette = []
for i in range(16):
    r = min(255, data[i * 3] * 4)
    g = min(255, data[i * 3 + 1] * 4)
    b = min(255, data[i * 3 + 2] * 4)
    palette.append((r, g, b))

decoder = EGADecoder(palette=palette)

# Decode from byte 768 onward
atlas = decoder.decode_planar(
    data[768:],
    width=320,
    height=200,
    msb_first=True
)
```

### Extracting Individual Textures
To extract a specific texture from the atlas:
1. Identify the texture's (x, y) coordinates in the 320×200 atlas
2. Determine the texture's width and height
3. Copy the pixel region from the decoded atlas image

```python
# Extract a texture at position (x, y) with size (w, h)
def extract_texture(atlas, x, y, w, h):
    pixels = []
    for row in range(h):
        for col in range(w):
            px = atlas.get_pixel(x + col, y + row)
            pixels.append(px)
    return Sprite(width=w, height=h, pixels=pixels, palette=atlas.palette)
```

## Usage in Game Engine
The game engine should:
1. Load MAZEDATA.EGA once at startup
2. Decode it into a 320×200 texture atlas using sequential planar format
3. Pre-extract commonly used textures into individual sprites
4. Map texture IDs to coordinates within the atlas
5. Render dungeon walls by blitting the appropriate texture

## File Format Comparison

| File | Size | Palette Header | Format |
|------|------|----------------|--------|
| TITLEPAG.EGA | 32,768 | ✓ (768 bytes) | Sequential planar |
| DRAGONSC.EGA | 32,768 | ✓ (768 bytes) | Sequential planar |
| GRAVEYRD.EGA | 32,768 | ✓ (768 bytes) | Sequential planar |
| **MAZEDATA.EGA** | 102,303 | ✗ (no header) | Sequential planar |

All use 320×200 resolution with 4-bit sequential planar encoding.

## Next Steps
1. ✅ Decode primary 320×200 texture atlas using correct sequential planar format
2. ⏳ Map texture coordinates for each dungeon tile type
3. ⏳ Analyze the remaining 70KB of data
4. ⏳ Determine texture ID → coordinate mapping
5. ⏳ Extract and catalog all wall/floor/ceiling textures
