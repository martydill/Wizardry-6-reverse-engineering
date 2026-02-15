# Wizardry 6 Style 3D Dungeon Renderer

Two first-person dungeon renderers using the MAZEDATA.EGA texture bands.

## Features

### Basic Renderer (`dungeon_renderer_3d.py`)
- First-person perspective rendering
- 3 depth levels (near, medium, far)
- Textured walls using MAZEDATA bands
- Grid-based movement
- Simple controls

### Enhanced Renderer (`dungeon_renderer_enhanced.py`)
- **5 depth levels** for better perspective
- **Minimap overlay** showing dungeon layout
- **Distance darkening** for depth perception
- **Side wall rendering** with perspective
- **Floor and ceiling** rendering
- **Multiple wall types** (different texture bands)
- Toggle minimap with 'M' key

## Running the Renderers

### Basic Version
```bash
python dungeon_renderer_3d.py
```

### Enhanced Version
```bash
python dungeon_renderer_enhanced.py
```

## Controls

| Key | Action |
|-----|--------|
| **↑** | Move forward |
| **↓** | Move backward |
| **←** or **Q** | Turn left |
| **→** or **E** | Turn right |
| **M** | Toggle minimap (enhanced only) |
| **ESC** | Quit |

## How It Works

### Texture Band System

The renderer uses the 6 texture bands from MAZEDATA.EGA:

```
Band 0 (y=0-32):   Stone wall texture (gray/colorful)
Band 1 (y=32-64):  Red brick pattern
Band 2 (y=64-96):  Blue tiled floor
Band 3 (y=96-128): Dark/void texture
Band 4 (y=128-160): Gray stone
Band 5 (y=160-200): Purple decorative
```

### Rendering Pipeline

1. **Clear screen** with floor/ceiling colors
2. **Render walls** from far to near:
   - Distance 5 (very far): 50×40 pixels
   - Distance 4 (far): 80×80 pixels
   - Distance 3 (medium-far): 140×140 pixels
   - Distance 2 (medium): 240×220 pixels
   - Distance 1 (near): 400×360 pixels
3. **Apply perspective**:
   - Walls scale based on distance
   - Side walls are narrower (1/4 width)
   - Distance darkening applied
4. **Draw minimap** (optional overlay)
5. **Draw HUD** with position and controls

### Wall Rendering

For each wall:
```python
# 1. Get texture band based on tile type
texture = textures.get_band(tile_type - 1)

# 2. Scale to wall dimensions
scaled = pygame.transform.scale(texture, (width, height))

# 3. Apply distance darkening
darkness = 1.0 - (distance - 1) * 0.15

# 4. Darken side walls for depth
if side_wall:
    darkness *= 0.7

# 5. Render to screen
screen.blit(scaled, (x, y))
```

### Dungeon Layout

The test dungeon is a 10×12 grid:
- `0` = Empty walkable space
- `1` = Stone wall (Band 0)
- `2` = Brick wall (Band 1)
- `3` = Blue tiles (Band 2)

```python
dungeon = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 2, 0, 0, 0, 0, 0, 3, 1],
    [1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1],
    # ... etc
]
```

## Perspective System

The renderer uses a classic tile-based perspective system:

### Distance Calculation
```
Player position: (px, py)
Player direction: North/East/South/West

For distance D:
  dx, dy = direction_delta * D
  check_x, check_y = px + dx, py + dy
```

### Wall Sizing
Walls get smaller with distance:

| Distance | Width | Height | Visual Effect |
|----------|-------|--------|---------------|
| 1 (near) | 400px | 360px  | Large, fills view |
| 2 | 240px | 220px  | Medium size |
| 3 | 140px | 140px  | Smaller |
| 4 | 80px  | 80px   | Far away |
| 5 (far) | 50px  | 40px   | Very distant |

### Side Walls
Side walls (left/right) are rendered at 1/4 the width of front walls to simulate perspective foreshortening.

## Minimap

The enhanced renderer includes an overlay minimap:

- **Position**: Top-right corner
- **Size**: 150×150 pixels
- **Display**:
  - Gray squares = walls
  - Dark squares = empty space
  - Yellow dot = player position
  - Yellow line = facing direction
  - Color coding by wall type

## Texture Sampling

The renderer samples textures as follows:

```python
# For a wall of size (width, height)
for px in range(width):
    for py in range(height):
        # Map screen pixel to texture pixel
        tex_x = (px * texture_width // width) % texture_width
        tex_y = (py * texture_height // height) % texture_height

        # Get color from texture band
        color = texture.get_pixel(tex_x, tex_y)

        # Draw to screen
        screen.set_at((x + px, y + py), color)
```

## Performance

- **Target FPS**: 30
- **Resolution**: 640×480 (basic) / 800×600 (enhanced)
- **Texture cache**: Texture bands pre-converted to pygame surfaces
- **Optimization**: Back-to-front rendering eliminates overdraw

## Extending the Renderer

### Adding New Dungeon Levels

Edit the `dungeon` array in the renderer:
```python
self.dungeon = [
    [1, 1, 1, ...],  # Your custom layout
    [1, 0, 0, ...],
    # ... etc
]
```

### Adding More Texture Bands

Modify the texture band extraction to use different Y ranges from MAZEDATA.EGA:
```python
band_configs = [
    (0, 32),    # Band 0
    (32, 64),   # Band 1
    # Add more ranges from the 70KB of additional data
]
```

### Improving Perspective

For more accurate perspective:
- Implement true ray-casting
- Add texture perspective correction
- Apply column-based rendering
- Add shading based on wall angle

## Comparison to Wizardry 6

### Similar:
- ✅ Tile-based grid movement
- ✅ First-person perspective
- ✅ Textured walls
- ✅ Distance-based sizing
- ✅ Cardinal directions only

### Different:
- ❌ Simpler perspective (no true ray-casting)
- ❌ Basic floor/ceiling (solid colors vs textured)
- ❌ No animated sprites
- ❌ No lighting effects
- ❌ Simpler side wall rendering

## Next Steps

Potential enhancements:
1. Load actual Wizardry 6 dungeon maps from SCENARIO.DBS
2. Add monster sprites (from MON*.PIC files)
3. Implement combat system
4. Add item/treasure rendering
5. Implement true ray-casting for smoother perspective
6. Add texture perspective correction
7. Implement floor/ceiling texturing using MAZEDATA bands
8. Add door opening animations
9. Implement lighting and shadows

## References

- `docs/MAZEDATA_TEXTURE_ORGANIZATION.md` - Texture band analysis
- `docs/MAZEDATA_FORMAT.md` - File format specification
- `compare_formats.py` - Format comparison analysis
- `extract_texture_bands.py` - Texture extraction utility
