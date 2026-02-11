# SCENARIO.DBS Graphic & Map Data Section Analysis

## Section Overview
- **Offset**: 0x9409 - 0x154E6
- **Size**: 49,373 bytes (48.2 KB)
- **Structure**: 125 data blocks separated by zero-padding

## Discovered Structures

### Block 1: First Small Block (0x009409, 23 bytes)
```
01 01 00 01 01 02 03 04 05 06 07 05 06 07 08 09 0A 08 09 0A 08 09 0A
```
- **Characteristics**: All values 0-10 (4-bit range)
- **11 unique bytes** - matches race count!
- **Possible interpretation**: Index array or mapping table

### Block 2: Large Block (0x009468, 740 bytes)
- **Possible structures**:
  - 37 records × 20 bytes
  - 20 records × 37 bytes
- Contains mixed data with ~59% zero bytes
- **Region of interest at 0x009508**:
  ```
  009508: 20 20 A0 28 A8 A8 00 00 00 00 00 00 00 00 00 00
  009518: 00 00 00 00 00 00 A8 A8 A0 28 20 20 A8 A8 00 00
  009528: 22 00 2A A0 00 A8 28 A8 28 A8 28 00 38 00 28 5A
  009538: 80 28 80 2A 02 20 82 02 82 02 80 02 C0 02 8A 02
  009548: 28 0A 28 0A 08 0A 28 0A 28 0A 28 0A 28 A3 28 0A
  009558: 8A 02 8A 02 0A 02 8A 02 8A 02 8A 02 8C 02 8A 02
  ```
  This shows repeating patterns and structured data!

### Block at 0x00A0B3 (224 bytes)
- **Possible interpretation**: 14 records × 16 bytes (matches CLASS count!)
- 79% zero bytes
- Values range 0-192
- Very sparse data - might be feature flags or boolean attributes

### Block at 0x00A609 (25 bytes)
```
02 00 00 00 00 00 00 00 00 00 00 00 00 00 00 05 00 00 00 0E 00 00 00 00 02
```
- Only 4 unique values: 0, 2, 5, 14
- **14** appears - class count?
- Very sparse, looks like configuration or index table

## Data Block Classification

### High 4-bit Content (Likely Tile Graphics)
Blocks with >80% bytes in 0-15 range:
- 0x009409 (100% low bytes, 23 bytes)
- 0x00A609 (100% low bytes, 25 bytes)
- 0x00A0B3 (86.6% low bytes, 224 bytes)

### Binary Tables
Blocks with mixed data, 50-80% low bytes:
- 0x009468 (740 bytes) - Possibly race/class attributes
- 0x0099AA (758 bytes)

### Text/String Regions
Blocks with >50% ASCII printable characters:
- 0x00A356 (155 bytes, 52% ASCII) - Might contain string data or compressed text

## Sprite ID References
- Found 43,738 bytes in range 0-58 (valid sprite IDs for MON00.PIC - MON58.PIC)
- These are scattered throughout the section
- Likely part of monster encounter definitions

## Next Steps to Investigate

1. **Examine 0x009508 region** - The repeating pattern structure suggests a table
2. **Decode tile graphics** - Blocks with 100% low bytes might be 4-bit planar tiles
3. **Parse 224-byte block at 0x00A0B3** - Strong candidate for 14-class table
4. **Map sprite ID references** - Create encounter table by finding sprite ID + stats patterns
5. **Look for map grid data** - Search for repeating patterns in 20x20 or 28x28 structures

## Known Game Data Context

From the game manual and other files:
- 11 playable races
- 14 playable classes
- 7 primary stats (STR, INT, PIE, VIT, DEX, SPD, KAR)
- Castle level 1-9 maps (varying sizes)
- 59 monster sprite files (MON00.PIC - MON58.PIC)
- 186 defined monsters (from monster table)

## Hypotheses

1. **0x009409-0x009468**: Index/lookup tables mapping tile IDs or sprite IDs
2. **0x009468-0x009B4E**: Race/class attribute tables (stat modifiers, restrictions)
3. **0x00A0B3-0x00A193**: Class feature/ability flags (14 × 16 bytes)
4. **Remaining large blocks**: Map layout data, encounter zones, event triggers

## Tools Created
- `tools/analyze_gfx_section.py` - Scans for data blocks and patterns
- `tools/identify_gfx_structures.py` - Attempts to identify race/class tables
- `tools/examine_specific_blocks.py` - Detailed hex analysis of key blocks
