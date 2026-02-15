# Wizardry 6 - Map Feature Format (4-bit)

This document describes the binary format for special map features (fountains, sconces, etc.) found in `SCENARIO.DBS`. These features are stored separately from the wall layout data.

## Location & Scope
- **File**: `SCENARIO.DBS` (or `newgame.dbs`)
- **Map 10 Offset**: `0x7D22`
- **Map 10 Size**: 128 bytes
- **Dimensions**: 16x16 cells

## Layout Organization
The map is divided into **8x8 quadrants**. Each quadrant is stored as a contiguous 32-byte block. The quadrants are stored in the following order:

1.  **Quadrant 0 (Top-Left)**: Coordinates `(0,0)` to `(7,7)`
2.  **Quadrant 1 (Top-Right)**: Coordinates `(8,0)` to `(15,7)`
3.  **Quadrant 2 (Bottom-Left)**: Coordinates `(0,8)` to `(7,15)`
4.  **Quadrant 3 (Bottom-Right)**: Coordinates `(8,8)` to `(15,15)`

## Cell Encoding
Each cell is represented by **4 bits (one nibble)**. Two cells are packed into each byte.

- **Order**: Row-major within each quadrant.
- **Bit Packing**:
    - **Even Cell Index**: Low Nibble (`bits 0-3`)
    - **Odd Cell Index**: High Nibble (`bits 4-7`)

### Index Calculation
To find the byte and nibble for a coordinate `(x, y)` within a 16x16 map:

1.  Determine Quadrant:
    - `qx = x // 8`, `qy = y // 8`
    - `q_idx = qy * 2 + qx`
2.  Determine Local Coordinates:
    - `lx = x % 8`, `ly = y % 8`
3.  Calculate Byte Offset:
    - `local_cell_idx = ly * 8 + lx`
    - `byte_offset = (q_idx * 32) + (local_cell_idx // 2)`
4.  Determine Nibble:
    - If `local_cell_idx` is even: Low Nibble
    - If `local_cell_idx` is odd: High Nibble

## Feature ID Table
Based on analysis of Map 10:

| ID | Feature | Description |
| :--- | :--- | :--- |
| `0x0` | Empty | No special feature |
| `0x1` | Stairs Up | Ascent to the floor above |
| `0x2` | Stairs Down | Descent to the floor below |
| `0x3` | Sconce | Wall-mounted light source |
| `0x4` | Fountain | Interactive water source |
| `0x5` | Secret Button | Wall-mounted trigger |
| `0x6` | Pressure Plate | Floor-mounted trigger |
| `0x7` | Portcullis | Iron gate |
| `0x8` | Shackles | Wall-mounted chains |
| `0x9` | Niche | Wall-mounted storage/alcove |
| `0xA` | Blue Box Niche | Specialized niche with blue box graphic |
| `0xB` | Red Box Niche | Specialized niche with red box graphic |
| `0xC` | Bones Niche | Specialized niche with bones graphic |
| `0xD` | Fake Water | Decorative/trap water floor |
| `0xE` | Pit Down | Hole in the floor (descend) |
| `0xF` | Pit Up | Hole in the ceiling (from the floor below) |

## Example: Bottom-Right Corner (15, 15)
- **Quadrant**: `qx=1, qy=1` -> **Q3** (starts at `0x7D82`)
- **Local**: `lx=7, ly=7`
- **Local Index**: `7 * 8 + 7 = 63`
- **Byte**: `0x7D82 + (63 // 2) = 0x7D82 + 31 = 0x7DA1`
- **Nibble**: 63 is odd -> **High Nibble**
- **Result**: The feature for (15, 15) is the high nibble of byte `0x7DA1`.
