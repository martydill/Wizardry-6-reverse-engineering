# MAZEDATA.EGA Texture Organization

## Key Discovery: Horizontal Texture Bands

After extensive analysis comparing with monster .PIC files and other .EGA files, we've determined that **MAZEDATA.EGA stores wall/floor/ceiling textures as horizontal bands**.

## Structure

```
MAZEDATA.EGA (102,303 bytes total)

Bytes 0-31,999: Main texture atlas (320×200 pixels)
  ├─ Band 0 (y=0-32):   Colorful stone/brick texture (13 colors)
  ├─ Band 1 (y=32-64):  Red/orange brick pattern (16 colors)
  ├─ Band 2 (y=64-96):  Blue tiled pattern (16 colors)
  ├─ Band 3 (y=96-128): Dark/black section (8 colors)
  ├─ Band 4 (y=128-160): Gray stone texture (16 colors)
  └─ Band 5 (y=160-200): Blue/purple patterns (16 colors)

Bytes 32,000-102,302: Additional texture data (70,303 bytes)
  - Possibly more texture variants
  - Animation frames
  - Different dungeon areas
```

## Texture Band System

### How It Works

Each 32-pixel tall band spans the full 320-pixel width and represents a complete texture that can be sampled by the 3D renderer:

1. **Full-width textures**: Each band is 320 pixels wide, allowing for:
   - Seamless horizontal tiling
   - Perspective-correct sampling
   - Different texture variations across the width

2. **Multiple bands for variety**: 6 main bands provide different wall/floor types:
   - Stone walls
   - Brick walls
   - Tiled floors
   - Darkness/void
   - Alternative stone textures
   - Decorative patterns

3. **3D Rendering Usage**: The game likely:
   - Samples horizontal strips from these bands
   - Scales/stretches them for perspective
   - Applies them to wall faces at different distances
   - Tiles them horizontally for long walls

## Comparison with Other Formats

### Monster .PIC Files
- **Format**: RLE-compressed tiled planar (8×8 tiles)
- **Content**: Individual monster sprites with multiple frames
- **Size**: Variable (typically 24×40, 48×68, 88×96 pixels)
- **Usage**: Character/monster rendering

### TITLEPAG/DRAGONSC/GRAVEYRD.EGA
- **Format**: Sequential planar with 768-byte VGA palette header
- **Content**: Full-screen 320×200 images
- **Size**: Exactly 32,768 bytes
- **Usage**: Title screens, story images

### MAZEDATA.EGA
- **Format**: Sequential planar, NO palette header (uses DEFAULT_16_PALETTE)
- **Content**: Horizontal texture bands for 3D dungeon rendering
- **Size**: 102,303 bytes (multiple texture sets)
- **Usage**: Wall/floor/ceiling textures for first-person 3D view

## Band Height Variations

Analysis shows textures could be organized in multiple ways:

### 32-pixel bands (6 total)
Best match for main wall textures:
- Band 0: 13 colors - Complex stone pattern
- Band 1: 16 colors - Brick wall
- Band 2: 16 colors - Blue tiles
- Band 3: 8 colors - Dark/void
- Band 4: 16 colors - Gray stone
- Band 5: 16 colors - Purple pattern

### 16-pixel bands (12 total)
Finer subdivision for wall details:
- Allows for more texture variety
- Better matches perspective scaling
- More efficient for near/far walls

### 8-pixel bands (25 total)
Maximum granularity:
- Very fine texture control
- Possible for floor/ceiling strips
- May represent different distances in 3D view

## How Wizardry 6 Likely Uses These Textures

In a typical first-person dungeon crawler:

1. **Wall Rendering**:
   - Left wall: Sample from band X
   - Right wall: Sample from band Y
   - Front wall: Sample from band Z
   - Scale vertically based on distance

2. **Floor/Ceiling**:
   - Sample horizontal strips
   - Apply perspective transformation
   - Tile as needed for depth

3. **Texture Selection**:
   - Dungeon tile type → texture band ID
   - Game logic maps tile types to Y-coordinate ranges
   - Different areas use different bands

## Next Steps

1. ✅ Successfully decoded MAZEDATA.EGA format
2. ✅ Identified horizontal band organization
3. ✅ Extracted individual texture bands
4. ⏳ Analyze remaining 70KB of data
5. ⏳ Determine exact mapping: dungeon tile type → texture band
6. ⏳ Understand how game samples these bands for 3D rendering
7. ⏳ Implement 3D wall renderer using these textures

## Tools Created

- `compare_formats.py` - Compare MON*.PIC, .EGA files, and MAZEDATA
- `analyze_tile_patterns.py` - Search for repeating patterns
- `visualize_atlas_grid.py` - Overlay grids to find organization
- `extract_texture_bands.py` - Extract individual texture bands
- Generated outputs:
  - `output/monsters/` - Decoded monster sprites
  - `output/texture_bands/` - Individual texture bands
  - `output/texture_catalog.png` - All bands visualized together
  - `output/grids/` - Grid overlay visualizations

## Files

- Main atlas: `tools/output/mazedata_atlas.png`
- Texture catalog: `output/texture_catalog.png`
- Individual bands: `output/texture_bands/band_32px_row*.png`
- Grid overlays: `output/grids/grid_32x32.png`
