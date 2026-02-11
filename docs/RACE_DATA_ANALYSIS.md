# Wizardry 6 Race Data Analysis - SCENARIO.DBS

## Executive Summary

Attempted to locate and decode race statistics from SCENARIO.DBS. While we found structured data that *appears* to be race-related, **the encoding does NOT match expected patterns** for simple stat values or bonus point costs.

## What We Found

### 1. **Race Index Block** (0x009409, 23 bytes) ✅ CONFIRMED

This block contains **exactly 11 unique values (0-10)** matching the 11 playable races:

```
Raw bytes: 01 01 00 01 01 02 03 04 05 06 07 05 06 07 08 09 0A 08 09 0A 08 09 0A
Values:     1  1  0  1  1  2  3  4  5  6  7  5  6  7  8  9 10  8  9 10  8  9 10
```

**Frequency distribution:**
- Elf (1): 4 occurrences
- Felpurr (8), Rawulf (9), Mook (10): 3 occurrences each
- Faerie (5), Lizardman (6), Dracon (7): 2 occurrences each
- Human (0), Dwarf (2), Gnome (3), Hobbit (4): 1 occurrence each

**Interpretation:** This is likely a **race availability lookup table** or **encounter frequency table**. The repetition pattern might indicate:
- Starting race availability tiers
- Enemy encounter weights by race type
- NPC spawn frequencies

### 2. **Structured Data Block** (0x009508+) ⚠️ UNCERTAIN

Found data that could be interpreted as **11 races × 14 classes**, but values don't match known game mechanics:

| Race | Fighter | Mage | Priest | ... | Pattern |
|------|---------|------|--------|-----|---------|
| Human | 32 | 32 | 160 | ... | Values in first half, zeros in second |
| Elf | 0 | 0 | 0 | ... | Zeros in first half, values in second (INVERTED!) |
| Dwarf | 168 | 168 | 0 | ... | Mixed pattern |

**Problems:**
1. ❌ Values don't match known stat ranges (8-13 for starting stats)
2. ❌ Values too large for bonus point costs (should be ~5-25)
3. ❌ No correlation found with documented race statistics
4. ❌ Elf row showing inverse pattern (zeros where Human has values)

### 3. **Known Race Statistics** (from online sources)

For reference, documented Wizardry 6 race starting stats:

| Race | STR | INT | PIE | VIT | DEX | SPD | Notes |
|------|-----|-----|-----|-----|-----|-----|-------|
| **Human** | 9 | 8 | 8 | 9 | 8 | 8 | Balanced |
| **Elf** | 7 | 10 | 10 | 7 | 9 | 8 | High INT/PIE, low STR/VIT |
| **Dwarf** | 11 | 6 | 10 | 12 | 7 | 7 | High STR/VIT, low INT |
| **Gnome** | 10 | 7 | 13 | 10 | 6 | 7 | Highest PIE |
| **Hobbit** | 8 | 7 | 6 | 9 | 10 | 11 | High DEX/SPD |

Sources:
- [Wizardry Character Classes - Zimlab](https://www.zimlab.com/wizardry/recovered/avenstar/classes.html)
- [Wizardry 8 Character Guide - GameFAQs](https://gamefaqs.gamespot.com/pc/374906-wizardry-8/faqs/41767) (Cosmic Forge Saga shared stats)

**Additional races** (Faerie, Lizardman, Dracon, Felpurr, Rawulf, Mook) have stat modifiers relative to Human baseline.

## Hypotheses for the 0x009508 Data

### Hypothesis 1: Encoded Racial Class Restrictions

The large values (160, 168) could be **bitmasks** indicating:
- Which equipment types the race can use
- Which spells are restricted
- Special racial abilities

### Hypothesis 2: Race/Class Compatibility Matrix

The pattern where Elf is inverted from Human suggests this might encode:
- Class difficulty/availability by race
- Profession change restrictions
- Multiclass path permissions

### Hypothesis 3: Not Race Data At All

This region might be:
- **Map tile definitions** (wall types, floor textures)
- **Encounter zone data** (monster spawn locations)
- **Event trigger parameters**

And the actual race stats are stored **elsewhere** in the file!

## Where Might Race Stats Actually Be?

### Candidate Locations NOT Yet Checked:

1. **In the first 0x9409 bytes** - Before the "Graphic & Map Data" section
   - Could be with XP tables or item tables

2. **Hard-coded in the executable** - WROOT.EXE
   - Common for constant game data

3. **In a different file** - NEWGAME.DBS
   - Character creation data often separate

4. **Encoded differently** - Not raw values but formulas
   - Could be stored as (base_value << 4) | modifier
   - Could use lookup tables with indices

## Next Steps

### To Find Race Statistics:

1. ✅ **Search NEWGAME.DBS** - Character creation file
   - Likely contains starting character templates
   - May have race stat baselines

2. ⏳ **Analyze items.csv race restrictions**
   - Item table at 0x000380 has race restriction bits
   - Could reverse-engineer race IDs from item data

3. ⏳ **Decode the 23-byte index completely**
   - Understand why races appear with different frequencies
   - Map to actual game mechanics (encounters? NPCs?)

4. ⏳ **Check executable (WROOT.EXE)**
   - Stats might be compiled into the binary
   - Use a hex editor to search for sequence: 09 08 08 09 08 08 (Human stats)

5. ⏳ **Re-examine 0x009508 with different record sizes**
   - Try 11 races × 7 stats
   - Try 11 races × 8 stats (+ personality/karma)
   - Look for encoded values (bit-shifted, offset, etc.)

### To Validate Current Findings:

1. **Test the race index (0x009409)**
   - Cross-reference with monster encounter data
   - Check if frequencies match game difficulty curves

2. **Compare with item race restrictions**
   - Item table has race bitmasks
   - See if patterns align

3. **Look for stat progression tables**
   - Level-up bonuses by race
   - HP/SP calculations by race

## Confidence Levels

| Finding | Confidence | Evidence |
|---------|-----------|----------|
| 23-byte block = race index | **85%** | 11 unique values, perfect race count match |
| 0x009508 = race/class table | **40%** | Right size but wrong values |
| 0x009508 = bonus point costs | **20%** | Values too large |
| 0x009508 = something else | **60%** | Values don't match any known mechanic |
| Race stats elsewhere in file | **70%** | No correlation found yet |

## Tools Created

- `tools/analyze_race_data.py` - Attempts to correlate binary data with known stats
- `tools/decode_race_bonus_points.py` - Analyzes potential bonus point tables
- This document: `RACE_DATA_ANALYSIS.md`

## Sources

- [Creating a Party - Crimson Tear](https://www.crimsontear.com/gaming/wizardry-6/party)
- [Statistics and Skills - Crimson Tear](https://www.crimsontear.com/gaming/wizardry-6/stats)
- [Wizardry 6 Manual (Archive.org)](https://archive.org/stream/Wizardry_6_Bane_of_the_Cosmic_Forge/Wizardry_6_Bane_of_the_Cosmic_Forge_djvu.txt)
- [Wizardry Character Classes - Zimlab](https://www.zimlab.com/wizardry/recovered/avenstar/classes.html)
- [Wizardry VI Solution](https://the-spoiler.com/RPG/Sir-Tech/wizardry.6.1/WIZ6.HTM)
- [Cosmic Forge Saga Races - Fandom](https://wizardry.fandom.com/wiki/Category:Cosmic_Forge_Saga_races)

## Conclusion

While we successfully identified what appears to be a **race index table** (85% confidence), the actual race statistics remain elusive. The data at 0x009508 is structured and race-related, but doesn't encode stats or bonus points in the expected format.

**Recommendation:** Search NEWGAME.DBS next, as it's specifically for character creation and likely contains race baseline stats.
