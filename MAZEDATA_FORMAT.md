# MAZEDATA.EGA File Format

## Overview
MAZEDATA.EGA contains all wall, floor, and ceiling textures for Wizardry 6's dungeon renderer.

## File Format
- **Type**: EGA texture atlas image
- **Dimensions**: 320×200 pixels
- **Color**: 16 colors (EGA palette)
- **Storage**: Row-interleaved planar format
- **Size**: 102,303 bytes total (32,000 bytes of image data + additional data)

## Structure

### Image Data (bytes 0-31,999)
The first 32,000 bytes contain a 320×200 EGA image in row-interleaved planar format:

```
Each scanline consists of 4 planes:
- Plane 0: 40 bytes (320 pixels / 8 bits)
- Plane 1: 40 bytes
- Plane 2: 40 bytes
- Plane 3: 40 bytes
Total: 160 bytes per scanline × 200 scanlines = 32,000 bytes
```

### Additional Data (bytes 32,000+)
The remaining ~70KB contains additional textures or animation frames (TBD - needs further analysis).

## Image Content
The 320×200 texture atlas contains:
- **Stone/brick wall textures** in various styles (top rows)
- **Floor textures**
- **Ceiling textures**
- **Door textures**
- **Special effects** (darkness, magical barriers, etc.)

Textures appear to be arranged in:
- 8×8 pixel tiles
- 16×16 pixel tiles
- Possibly larger composite textures

## Decoding

### Python Example
```python
from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE
from PIL import Image

# Read file
with open("MAZEDATA.EGA", "rb") as f:
    data = f.read()

# Decode first 32KB as 320x200 EGA image
decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
atlas = decoder.decode_planar_row_interleaved(
    data[:32000],
    width=320,
    height=200
)

# Save as PNG
img = Image.frombytes("RGB", (atlas.width, atlas.height), atlas.to_rgb_bytes())
img.save("mazedata_atlas.png")
```

### Extracting Individual Textures
To extract a specific texture from the atlas:
1. Identify the texture's (x, y) coordinates in the 320×200 atlas
2. Determine the texture's width and height
3. Copy the pixel region from the decoded atlas image

```python
# Extract 32×32 texture at position (x=0, y=0)
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
2. Decode it into a 320×200 texture atlas
3. Pre-extract commonly used textures (walls, floors, ceilings) into individual sprites
4. Store texture coordinates or IDs for each dungeon tile type
5. Render dungeon walls by blitting the appropriate texture

## Comparison to Other Files
- **TITLEPAG.EGA**: 32,768 bytes = exact 320×200 EGA image
- **DRAGONSC.EGA**: 32,768 bytes = exact 320×200 EGA image
- **GRAVEYRD.EGA**: 32,768 bytes = exact 320×200 EGA image
- **MAZEDATA.EGA**: 102,303 bytes = 320×200 atlas + 70KB additional data

All use the same row-interleaved planar EGA format.

## Next Steps
1. ✅ Decode primary 320×200 texture atlas
2. ⏳ Map out which textures are located where in the atlas
3. ⏳ Analyze the remaining 70KB of data
4. ⏳ Determine how the game references textures (by coordinates? by ID?)
5. ⏳ Extract and catalog all wall/floor/ceiling textures
