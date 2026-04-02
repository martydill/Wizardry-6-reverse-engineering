# `PCFILE.DBS` File Format

This document summarizes the current reverse-engineered format of Wizardry 6
`PCFILE.DBS` as observed from:

- shipped sample data in PCFILE.dbs
- additional live saves 
- character viewer / character management code in `WPCVW.OVR`
- helper routines in `WROOT.EXE`

It is intended to be the current working format spec for loader work.

## Status Legend

- `confirmed`: directly supported by disassembly and/or data checks
- `partial`: structure is known, exact semantics are incomplete
- `unknown`: still unresolved

## Top-Level File Layout

Observed file header:

| Offset | Size | Type | Status | Meaning |
|---|---:|---|---|---|
| `0x00` | 2 | `u16` | confirmed | record size, usually `0x01B0` (432) |
| `0x02` | 2 | `u16` | confirmed | slot count, usually `0x0010` (16) |
| `0x04` | 2 | `u16` | confirmed | first record offset, usually `0x0018` |
| `0x06` | 18 | bytes | unknown | header bytes before first record |

Records are fixed-size and contiguous:

- `record_offset(slot) = first_record_offset + slot * record_size`
- in the shipped sample: `0x0018 + slot * 0x01B0`

Active records are identified by a non-empty 8-byte name field at the start of
the record.

## Record Layout

Each character record is `0x01B0` bytes.

### Offset Map

| Offset | Size | Type | Status | Meaning |
|---|---:|---|---|---|
| `0x000` | 8 | char[8] | confirmed | name, null-padded ASCII |
| `0x008` | 4 | `u32` | confirmed | age in days |
| `0x00C` | 2 | `u16` | unknown | unresolved early word |
| `0x00E` | 2 | `u16` | unknown | unresolved early word |
| `0x010` | 2 | `u16` | unknown | unresolved early word |
| `0x012` | 2 | `u16` | unknown | unresolved early word |
| `0x014` | 2 | `u16` | unknown | unresolved early word |
| `0x016` | 2 | `u16` | unknown | unresolved early word |
| `0x018` | 2 | `u16` | confirmed | HP current |
| `0x01A` | 2 | `u16` | confirmed | HP max |
| `0x01C` | 2 | `u16` | confirmed | stamina current |
| `0x01E` | 2 | `u16` | confirmed | stamina max |
| `0x020` | 2 | `u16` | confirmed | current load / encumbrance, tenths |
| `0x022` | 2 | `u16` | confirmed | max load / capacity, tenths |
| `0x024` | 2 | `u16` | confirmed | rank |
| `0x026` | 2 | `u16` | confirmed | level |
| `0x028` | 4 | 2 x `u16` | confirmed | fire spell points: current, max |
| `0x02C` | 4 | 2 x `u16` | confirmed | water spell points: current, max |
| `0x030` | 4 | 2 x `u16` | confirmed | air spell points: current, max |
| `0x034` | 4 | 2 x `u16` | confirmed | earth spell points: current, max |
| `0x038` | 4 | 2 x `u16` | confirmed | mental spell points: current, max |
| `0x03C` | 4 | 2 x `u16` | confirmed | magic spell points: current, max |
| `0x040` | `20 * 8` | entries | partial | inventory table, 20 entries of 8 bytes |
| `0x0E0` | `0x04C` | bytes | unknown | unresolved middle block |
| `0x12C` | 8 | `u8[8]` | confirmed | primary stat block |
| `0x134` | 30 | `u8[30]` | partial | skill block with six non-skill holes |
| `0x152` | `0x036` | bytes | unknown | unresolved pre-spell-known block |
| `0x188` | 12 | packed bits | confirmed | known-spell bitset, spell id = bit index |
| `0x194` | `0x009` | bytes | unknown | unresolved late block |
| `0x19D` | 1 | `u8` | confirmed | race id |
| `0x19E` | 1 | `u8` | confirmed | gender id |
| `0x19F` | 1 | `u8` | confirmed | class id |
| `0x1A0` | 5 | bytes | unknown | unresolved late block |
| `0x1A5` | 1 | `u8` | partial | cached viewer-derived byte |
| `0x1A6` | 3 | bytes | unknown | unresolved late block |
| `0x1A9` | 1 | `u8` | partial | input to viewer-derived status routine |
| `0x1AA` | 1 | `u8` | partial | input to viewer-derived status routine |
| `0x1AB` | 1 | `u8` | unknown | unresolved late byte |
| `0x1AC` | 1 | `u8` | confirmed | inventory page 1 count, slots `0..9` |
| `0x1AD` | 1 | `u8` | confirmed | inventory page 2 count, slots `10..19` |
| `0x1AE` | 2 | bytes | unknown | trailing unresolved bytes |

## Field Details

### Name

- Offset: `0x000..0x007`
- 8-byte null-padded ASCII
- empty name means unused slot in current tooling

### Age

- Offset: `0x008..0x00B`
- stored as a 32-bit little-endian day count
- `WPCVW` displays age as whole years by dividing by `365`

Examples:

- raw `7535` displays as age `20`
- raw `6590` displays as age `18`

### Vitals

- `0x018/0x01A` = HP current/max
- `0x01C/0x01E` = stamina current/max

These pairs are passed into the same viewer formatting routines.

### Load / Encumbrance

- `0x020` = current load
- `0x022` = max load

Both are stored in tenths. The viewer prints them after dividing by `10`.

`WPCVW` recomputes current load from inventory entries, which rules out older
guesses like gold / XP for these fields.

### Rank and Level

- `0x024` = rank
- `0x026` = level

The viewer prints them in `LVL, RNK` order, but the record stores `RNK` first.

Evidence:

- message label `0x00C8` includes `LVL RNK`
- level-up code increments `+0x26`
- spellbook-writing eligibility compares spell level against `+0x24`

### Spell Point Pools

Offsets:

- fire: `0x028..0x02B`
- water: `0x02C..0x02F`
- air: `0x030..0x033`
- earth: `0x034..0x037`
- mental: `0x038..0x03B`
- magic: `0x03C..0x03F`

Each school is stored as:

- first word = current points
- second word = max / base points

Important correction:

- these are not spell-known bitmasks
- known spells are stored separately in the 12-byte bitset at `0x188`

### Inventory Table

Inventory starts at `0x040` and contains 20 entries of 8 bytes each.

Entry layout:

| Entry Offset | Size | Type | Status | Meaning |
|---|---:|---|---|---|
| `+0x00` | 2 | `u16` | confirmed | item id |
| `+0x02` | 2 | `u16` | confirmed | load contribution in tenths |
| `+0x04` | 1 | `u8` | partial | subtype / category byte |
| `+0x05` | 1 | `u8` | partial | additional category / class byte |
| `+0x06` | 1 | `u8` | partial | quantity / charges-like byte |
| `+0x07` | 1 | `u8` | partial | flags / state bits |

What is known:

- `+0x02` matches item weight from `SCENARIO.DBS` for ordinary items
- `+0x06` is used as a multiplier for entries considered stackable/countable by
  viewer logic
- `+0x07 bit 0` is tested by inventory movement code, so it is a real state flag

What remains unresolved:

- the full meaning of `+0x04`
- the full meaning of `+0x05`
- the full bit layout of `+0x07`
- whether `+0x06` is always quantity vs. charges depending on item class

### Primary Stats

Offset `0x12C..0x133`, eight consecutive bytes:

| Offset | Stat |
|---|---|
| `0x12C` | strength |
| `0x12D` | intelligence |
| `0x12E` | piety |
| `0x12F` | vitality |
| `0x130` | dexterity |
| `0x131` | speed |
| `0x132` | personality |
| `0x133` | karma |

These are fully confirmed by viewer editing code.

### Skill Block

Offset `0x134`, size 30 bytes.

This is not a pure 30-skill array. Six bytes inside the block are not normal
skill slots.

| Index | Offset | Meaning |
|---|---:|---|
| `0` | `0x134` | wand_and_dagger |
| `1` | `0x135` | sword |
| `2` | `0x136` | axe |
| `3` | `0x137` | mace_and_flail |
| `4` | `0x138` | pole_and_staff |
| `5` | `0x139` | throwing |
| `6` | `0x13A` | sling |
| `7` | `0x13B` | bow |
| `8` | `0x13C` | shield |
| `9` | `0x13D` | hands_and_feet |
| `10` | `0x13E` | non-skill byte |
| `11` | `0x13F` | artifacts |
| `12` | `0x140` | music |
| `13` | `0x141` | oratory |
| `14` | `0x142` | legerdemain |
| `15` | `0x143` | skulduggery |
| `16` | `0x144` | ninjutsu |
| `17` | `0x145` | non-skill byte |
| `18` | `0x146` | non-skill byte |
| `19` | `0x147` | non-skill byte |
| `20` | `0x148` | non-skill byte |
| `21` | `0x149` | non-skill byte |
| `22` | `0x14A` | scouting |
| `23` | `0x14B` | mythology |
| `24` | `0x14C` | scribe |
| `25` | `0x14D` | alchemy |
| `26` | `0x14E` | theology |
| `27` | `0x14F` | theosophy |
| `28` | `0x150` | thaumaturgy |
| `29` | `0x151` | kirijutsu |

Confirmed spot checks:

- `+0x13D` is used by monk/ninja-related UI logic as `hands_and_feet`
- `+0x151` is used by the same logic as `kirijutsu`

The six non-skill bytes remain unresolved.

### Known Spells Bitset

- Offset: `0x188..0x193`
- size: 12 bytes = 96 bits
- meaning: packed known-spell ownership

Encoding:

- bit index `n` means spell id `n` is known
- spell ids run `0..81`
- byte index = `spell_id >> 3`
- bit mask = `1 << (spell_id & 7)`

This is directly proven by `WPCVW` calling shared `WROOT` bit-test and bit-set
helpers with the actual spell id.

### Race, Gender, Class

Offsets:

- `0x19D` = race id
- `0x19E` = gender id
- `0x19F` = class id

Current internal id maps used in tooling:

#### Race IDs

| ID | Name | Status |
|---:|---|---|
| `0` | Human | high confidence |
| `1` | Elf | high confidence |
| `2` | Dwarf | high confidence |
| `3` | Gnome | provisional but consistent |
| `4` | Hobbit | provisional |
| `5` | Faerie | provisional |
| `6` | Lizardman | high confidence |
| `7` | Dracon | provisional but consistent |
| `8` | Felpurr | high confidence |
| `9` | Rawulf | provisional |
| `10` | Mook | high confidence |
| `11` | unused_race_11 | unresolved / likely unused |
| `12` | unused_race_12 | unresolved / likely unused |
| `13` | unused_race_13 | unresolved / likely unused |

#### Gender IDs

| ID | Meaning |
|---:|---|
| `0` | male |
| `1` | female |

#### Class IDs

| ID | Name | Status |
|---:|---|---|
| `0` | Fighter | high confidence |
| `1` | Mage | high confidence |
| `2` | Priest | high confidence |
| `3` | Thief | high confidence |
| `4` | Ranger | high confidence |
| `5` | Alchemist | high confidence |
| `6` | Bard | high confidence |
| `7` | Psionic | high confidence |
| `8` | Valkyrie | provisional |
| `9` | Bishop | provisional |
| `10` | Lord | high confidence |
| `11` | Samurai | high confidence |
| `12` | Monk | provisional |
| `13` | Ninja | high confidence |

### Late Record Metadata

These bytes are used by `WPCVW`, but not fully decoded.

| Offset | Status | Current understanding |
|---|---|---|
| `0x1A5` | partial | cached byte written by viewer-derived routine at `0x50AA` |
| `0x1A9` | partial | input to viewer-derived routine |
| `0x1AA` | partial | input to viewer-derived routine |
| `0x1AC` | confirmed | inventory page 1 count |
| `0x1AD` | confirmed | inventory page 2 count |

The routine that derives `0x1A5` also uses:

- `0x020/0x022` load percentage
- `0x01E` stamina max
- `0x1A9`
- `0x1AA`

So `0x1A5` should currently be treated as cached UI state, not a primary
character attribute.

## Unknown / Unresolved Areas

The main unresolved parts of the record are:

### Early words `0x00C..0x016`

- present as six 16-bit words
- all zero in the shipped sample party
- no defended semantics yet

### Middle block `0x0E0..0x12B`

- not yet mapped
- likely contains additional status / progression / runtime-persisted data

### Skill holes in `0x134..0x151`

- bytes at skill indices `10`, `17`, `18`, `19`, `20`, `21`
- definitely stored in the block
- not yet identified as normal skills

### Block `0x152..0x187`

- unresolved
- sits immediately before the known-spell bitset

### Block `0x194..0x1A4`

- unresolved late-record bytes

### Inventory entry internals

Need a full decode of:

- per-entry state flags
- equipment / identified / cursed encoding
- exact meaning of category bytes
- precise interpretation of count-like byte across item classes

## Important Corrections Versus Older Guesses

These older assumptions are now known to be wrong:

- `0x020/0x022` are not gold / experience; they are current/max load
- `0x028..0x03F` are not spell-known masks; they are spell-point pools
- the real known-spell ownership is the packed bitset at `0x188..0x193`
- age is not just a raw 16-bit year count; it is stored as days and displayed
  as `days // 365`

## Practical Loader Guidance

For a defensible loader:

1. trust the file header fields at `0x00/0x02/0x04`
2. treat records as fixed-size `0x01B0`
3. decode known fields above
4. preserve unknown bytes exactly on write
5. treat unresolved fields as opaque raw data, not guessed semantics

## Related Docs

- [PCFILE_WPCVW_LOAD_NOTES.md](docs/PCFILE_WPCVW_LOAD_NOTES.md)
- [PCFILE_EDITOR.md](docs/PCFILE_EDITOR.md)
