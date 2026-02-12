# MAZEDATA.EGA Tile Format

**BREAKTHROUGH**: Successfully decoded the MAZEDATA.EGA tile descriptor format!

## File Structure

```
Offset       Size        Description
------------ ----------- ----------------------------------
0x000000     10,752      Tile descriptor table
0x002A00     91,551      Tile pixel data (planar format)
```

## Tile Descriptor Format

**4-byte records**: `[offset_le16][width_4px][height_4px]`

- **Offset** (2 bytes, LE16): Byte offset into tile data region (starts at 0x002A00)
- **Width** (1 byte): Width in 4-pixel units (multiply by 4 for pixel width)
- **Height** (1 byte): Height in 4-pixel units (multiply by 4 for pixel height)

Example:
```
Bytes:  85 03 08 08
Offset: 0x0385 (901 bytes into tile data)
Width:  0x08 × 4 = 32 pixels
Height: 0x08 × 4 = 32 pixels
```

## Tile Data Format

Each tile uses **planar 4bpp encoding**:
- 4 bitplanes, MSB-first
- Sequential planar (each plane stored completely before the next)
- Bytes per tile = (width × height) ÷ 2

## Statistics

- **Total metadata size**: 10,752 bytes (2,688 potential 4-byte records)
- **Valid descriptors**: 297 tiles
- **Invalid records**: Remaining bytes have invalid dimensions or out-of-bounds offsets

## Tile Dimensions

Tiles have **non-square dimensions**! Common sizes:

### Square tiles:
- 32×32, 56×56, 16×16

### Rectangular tiles:
- Wide: 156×108, 172×32, 240×36, 132×28, 48×72
- Tall: 32×244, 8×88, 16×72, 20×48
- Small: 4×32, 8×48, 32×8, 32×12

## Animation Frames

The varying dimensions suggest:
- **Non-square tiles** may be UI elements or decorations
- **Similar-sized groups** could be animation frames
- **Very tall tiles** (e.g., 32×244) might be vertical door/wall animations
- **Very wide tiles** (e.g., 240×36) might be horizontal decorations

## Implementation

See `extract_all_tile_descriptors.py` for full extraction code.

### Decoding algorithm:

```python
# Parse descriptor
offset = metadata[i] | (metadata[i+1] << 8)
width_px = metadata[i+2] * 4
height_px = metadata[i+3] * 4

# Extract tile data
required_bytes = (width_px * height_px) // 2
tile_data = file_data[0x002A00 + offset : 0x002A00 + offset + required_bytes]

# Decode planar format (4 planes, MSB-first)
decode_planar_tile(tile_data, width_px, height_px, palette)
```

## Next Steps

- ✅ Extract all 297 tiles
- ⏳ Group tiles by similarity (find animation sequences)
- ⏳ Map tile IDs to dungeon map data
- ⏳ Identify UI elements vs. wall/floor textures
- ⏳ Analyze remaining 70KB data after main tile region
