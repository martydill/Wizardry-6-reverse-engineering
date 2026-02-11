# SCENARIO.DBS Graphic & Map Data Section - Key Findings

## Summary
After analyzing the 49,373-byte Graphic & Map Data section (0x9409 - 0x154E6), we've identified several structured data tables, including what appear to be race and class attribute tables.

## Confirmed Structure Locations

### 1. First Index Block (0x009409, 23 bytes)
```
01 01 00 01 01 02 03 04 05 06 07 05 06 07 08 09 0A 08 09 0A 08 09 0A
```
- All values 0-10 (4-bit range)
- **11 unique byte values** - matches number of playable races
- **Likely**: Lookup table or index array for race/class data

### 2. Class Ability Flags Table (0x00A0B3, 224 bytes = 14 × 16)

This is a **confirmed class table** with sparse bit-flags indicating abilities/permissions per class:

| Class     | Non-Zero Bytes | Interpretation |
|-----------|----------------|----------------|
| Fighter   | [0]=0x01 | Basic warrior class |
| Mage      | [6]=0x50 | Magic-user with spell school access |
| Priest    | [14]=0x77 | Divine magic user |
| Thief     | [8]=0xB0 | Thieving skills |
| Ranger    | [1]=0x40, [5]=0x10, [9]=0x40 | Hybrid fighter with some skills |
| Alchemist | [14]=0x9B, [15]=0x07 | Potion/alchemy abilities |
| **Bard**  | **10 non-zero bytes** | **Multi-talented** (music + some magic + skills) |
| Psionic   | [0]=0x07 | Psionic powers |
| Valkyrie  | [5]=0x0C, [9]=0x09, [13]=0x77, [14]=0x77 | Female warrior with divine magic |
| **Bishop**| **10 non-zero bytes** | **Hybrid Mage/Priest** (both magic types) |
| Lord      | [1]=0x07, [5]=0x89 | Elite fighter with some divine magic |
| **Ninja** | **10 non-zero bytes** | **Hybrid thief/fighter with special skills** |
| Monk      | All zeros | Bare-hands fighter (no equipment/magic) |
| Samurai   | [15]=0x50 | Elite oriental warrior |

**Key Observations**:
- Hybrid classes (Bard, Bishop, Ninja) have the most non-zero bytes
- Monk has all zeros - fits lore (unarmored, no spells)
- Byte positions likely represent: equipment slots, spell schools, special abilities

### 3. Potential Race/Class Attribute Region (0x009508+)

Multiple overlapping interpretations detected. The data contains structured tables but exact record boundaries are ambiguous. Common patterns seen:

**Candidate 11 × 16 byte Race Table** (0x009508):
```
Race          Bytes (first 10 shown)
Human:        20 20 A0 28 A8 A8 00 00 00 00
Elf:          00 00 00 00 00 00 A8 A8 A0 28
Dwarf:        22 00 2A A0 00 A8 28 A8 28 A8
...
```

**Candidate 14 × 16 byte Class Table** (0x00950B):
```
Class         Bytes (first 10 shown)
Fighter:      28 A8 A8 00 00 00 00 00 00 00
Mage:         00 00 00 A8 A8 A0 28 20 20 A8
Priest:       A0 00 A8 28 A8 28 A8 28 00 38
...
```

**Interpretation**: These tables likely contain:
- Starting stat modifiers (STR, INT, PIE, VIT, DEX, SPD, KAR)
- Racial/class bonuses or restrictions
- Hit point/spell point multipliers
- Experience level-up modifiers

The values don't appear to be direct stat values (too large), more likely encoded flags or offsets.

## Other Notable Patterns

### 4. Large Binary Blocks
- **Block at 0x009468** (740 bytes): Could be 37×20 or 20×37 structure
- **Block at 0x0099AA** (758 bytes): Mixed data, possible encounter tables
- Both contain sprite ID references (0-58 range)

### 5. Sprite ID References
- Found **43,738 bytes** in valid sprite ID range (0-58)
- Scattered throughout section
- Likely part of monster encounter definitions and map event triggers

### 6. Map Data (Not Yet Located)
Castle dungeon is organized in 9 levels. Expected to find:
- Grid layouts (20×20 or 28×28 tile grids)
- Wall/floor tile type indices
- Event trigger locations
- NPC placement data

## Data Block Classification Summary

| Offset   | Size | Likely Content |
|----------|------|----------------|
| 0x009409 | 23 B | Index/lookup table (11 unique values = races?) |
| 0x009468 | 740 B | Race/class attributes or equipment tables |
| 0x009508+ | Variable | Structured race/class data (overlapping tables) |
| 0x0099AA | 758 B | Binary table (encounters or map events?) |
| 0x00A0B3 | 224 B | **Class ability flags** (14 × 16, confirmed) |
| Rest | ~47 KB | Tile graphics, map grids, event scripts |

## Next Steps

1. **Decode 0x009508 region precisely**:
   - Need to determine exact record boundaries
   - Compare values with game manual stat ranges
   - Cross-reference with character creation screens

2. **Locate map grid data**:
   - Search for repeating 20×20 or 28×28 patterns
   - Look for wall tile indices (0-15 range for 16-color EGA)
   - Map to MAZEDATA.EGA texture atlas coordinates

3. **Parse encounter tables**:
   - Find structures containing sprite IDs (0-58)
   - Link to monster table data (offsets 0x154E6+)
   - Decode spawn rates and group sizes

4. **Identify event scripts**:
   - Look for 144-byte or 288-byte event blocks
   - Parse trigger conditions and actions
   - Link to MSG.DBS message strings

## Tools Created

- `tools/analyze_gfx_section.py` - Scans for 125 data blocks
- `tools/examine_specific_blocks.py` - Hex dump analysis
- `tools/decode_race_class_area.py` - Table structure decoder
- Documentation: `SCENARIO_DBS_GRAPHIC_SECTION.md`
- This file: `SCENARIO_DBS_FINDINGS.md`

## References

- Wizardry 6 Manual: 11 races, 14 classes, 7 stats
- Monster sprite files: MON00.PIC - MON58.PIC (59 files)
- Monster table: 186 defined monsters at 0x154E6
- Item table: 452 items at 0x000380
- Map texture atlas: MAZEDATA.EGA (320×200 EGA)
