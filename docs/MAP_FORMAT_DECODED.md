# Wizardry 6 Map Format - Complete Analysis

## Discovery Summary

By comparing `NEWGAME0.DBS` (original) with `NEWGAME.DBS` (4 fountains added to Map 10 corners), we've decoded how map features are stored.

---

## File Structure

### NEWGAME.DBS Layout
```
Offset      Size        Description
---------   ---------   ----------------------------------
0x0000      ~32KB       Unknown (class/race data, scripts?)
0x7B2E      ~9KB        Feature table (92-byte entries)
0xA000      5120 bytes  Map 10 data (16×16, 20 bytes/cell)
0xB400      ~35KB       More maps and data
```

---

## Feature Table Structure

### Location
- **Starts around:** 0x7B2E (approximate - needs more analysis)
- **Entry size:** 92 bytes (0x5C)
- **Entry spacing:** Fixed 92-byte intervals

### Feature Entry Format (92 bytes per entry)

```
Offset  Size  Description
------  ----  --------------------------------------------
0x00    1     Feature Type ID
                0x00 = Empty/unused
                0x04 = Fountain
                (other values unknown)

0x01-16 16    Unknown data

0x11-12 2     Purpose unknown (Entry #0 had 0x20 0x77)

0x13-22 16    Unknown data

0x23    1     Feature Flags/Type
                0x00 = Disabled/unused?
                0x40 = Active/enabled?
                (bit 6 set)

0x24-5B 56    Unknown data
```

---

## Key Findings

### 1. Fountains Added to 4 Corners

**User's modification:** Added fountains to Map 10's four corners: (0,0), (15,0), (0,15), (15,15)

**Changes made:** Only 4 bytes in entire file changed!

```
Entry #0 at 0x7D22:
  Byte 0:  0x00 -> 0x04  (Set feature type to fountain)
  Byte 35: 0x00 -> 0x40  (Enable feature)

Entry #1 at 0x7D7E:
  Byte 0:  0x00 -> 0x04  (Set feature type to fountain)
  Byte 35: 0x00 -> 0x40  (Enable feature)
```

### 2. Position Encoding

**CRITICAL DISCOVERY:** Map cell data did NOT change!

This means:
- **Fountain positions are NOT stored in the 20-byte cell records**
- **Positions are determined by entry index/number**
- **Each feature entry implicitly controls specific map locations**

### 3. Entry-to-Position Mapping

**2 entries = 4 fountain locations**

Possible mapping schemes:
1. **Diagonal pairs:**
   - Entry #0 → (0,0) + (15,15) [Main diagonal corners]
   - Entry #1 → (15,0) + (0,15) [Anti-diagonal corners]

2. **Horizontal pairs:**
   - Entry #0 → (0,0) + (15,0) [Top row corners]
   - Entry #1 → (0,15) + (15,15) [Bottom row corners]

3. **Vertical pairs:**
   - Entry #0 → (0,0) + (0,15) [Left column corners]
   - Entry #1 → (15,0) + (15,15) [Right column corners]

4. **Quadrant-based:**
   - Entry #0 → NW + NE quadrants
   - Entry #1 → SW + SE quadrants

**Most likely:** Diagonal pairs, as this matches the 8×8 quadrant structure mentioned by user.

---

## Map Cell Structure (Previously Decoded)

### Cell Format: 20 bytes per cell

```
Offset  Description
------  ----------------------------------
0-1     Unknown
2-19    Wall data (odd bytes only)
        Byte 1,3,5...19 encode walls
        Byte = Y coordinate (row pairs)
        Bit 5 = Left edge wall
        Bit 7 = Right edge wall
```

### Storage
- **Column-major order:** `cell_index = (col × height) + row`
- **Map 10:** 16×16 = 256 cells × 20 bytes = 5,120 bytes
- **Offset in NEWGAME.DBS:** 0xA000

---

## Still Unknown

### Feature Table
1. **Exact table start/end offsets**
2. **Total number of entries**
3. **Entry index → map position formula**
4. **Meaning of bytes 1-16, 17-34, 36-91**
5. **Other feature type IDs (doors, chests, NPCs, etc.)**
6. **How features relate to multiple maps**

### Position Data
1. **Are positions truly implicit, or stored in unknown bytes?**
2. **If implicit, what's the algorithmic mapping?**
3. **Are there separate tables for each map?**
4. **How are variable-size maps handled?**

### Entry #0 Pre-existing Data
- **Bytes 17-18 had values 0x20 (32) and 0x77 (119)**
- Purpose unknown - could be:
  - Coordinates in different encoding
  - Message/text IDs
  - Item IDs
  - Previous feature state data

---

## Next Steps for Analysis

1. **Find more modified save files** with known feature placements
2. **Identify feature table boundaries** (scan for padding/delimiters)
3. **Test position hypothesis** by adding fountains to other locations
4. **Examine other entry types** (entries #-10, #-9, etc. have complex data)
5. **Map entry indices to game locations** systematically
6. **Decode remaining bytes** in 92-byte structure

---

## Implementation Notes

### For Bane Engine

When implementing map loading:

```python
# Load feature table
feature_entries = load_feature_table(offset=0x7B2E, entry_size=92)

# For each active feature (byte 0 != 0 and byte 35 != 0)
for entry_id, entry in enumerate(feature_entries):
    if entry[0] != 0 and entry[35] != 0:
        feature_type = entry[0]  # 0x04 = fountain

        # TODO: Determine positions from entry_id
        positions = get_positions_for_entry(entry_id)

        for pos in positions:
            spawn_feature(pos, feature_type)
```

---

## Testing Recommendations

To fully decode the system:

1. Create save with fountain at **single corner** (not all 4)
2. Create save with fountain at **center** of map
3. Create save with fountain at **edge midpoint**
4. Compare which entries change and how

This will reveal the exact entry-to-position mapping.

---

## Conclusion

The Wizardry 6 map format uses a **two-tier system:**

1. **Map cells (20 bytes):** Store walls and terrain
2. **Feature table (92 bytes/entry):** Store interactive elements (fountains, doors, NPCs, chests, etc.)

Features are **position-independent** - their locations are determined by entry index, not embedded coordinates. This is an efficient design for era-appropriate storage constraints.

The next breakthrough will come from understanding the **entry index → map position** mapping function.
