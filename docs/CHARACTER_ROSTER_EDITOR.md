# Character Roster Editor (WinForms, .NET Framework 4.8)

A modern WinForms editor for `PCFILE.DBS` character rosters.

- Solution path: `apps/character_roster_editor/CharacterRosterEditor.sln`
- Target framework: `.NET Framework 4.8`
- UI: modern light theme, roster grid + detail editor pane

## Features

- Open and save Wizardry 6 `PCFILE.DBS` files.
- Delete a selected character slot (clears the record to an empty slot).
- Displays all character slots from the file header table.
- Displays portrait preview from `WPORT0.EGA` / `WPORT1.EGA`, searching common locations (same folder as `PCFILE.DBS`, local `gamedata/`, parent folder, and parent `gamedata/`), using raw portrait selector bytes from the character late-record area.
- Uses a compact Core layout with primary identity fields (name/age/level/rank) and stats shown side-by-side.
- Editable fields (all currently known fields from the documented format):
  - Name
  - Age (years, stored back as days)
  - Level / Rank
  - HP / Stamina current and max
  - Load current/max (tenths)
  - Spell points (current/max) for Fire, Water, Air, Earth, Mental, Magic
  - Race / Gender / Class
  - Primary stats (STR, INT, PIE, VIT, DEX, SPD, PER, KAR)
  - Confirmed skill entries from the 30-byte skills block (unresolved non-skill bytes are preserved but hidden)
  - 20 inventory entries (`item id`, `load`, and bytes `+0x04..+0x07`)
  - Inventory page counts (`0x1AC`, `0x1AD`)
  - Full 12-byte known-spells bitset (hex editor)
- Preserves unknown bytes in each record by keeping the raw record and writing back only known mapped fields.
- Prevents silent edits when loading unusual values by:
  - supporting full `u16` ranges for rank/level/HP/stamina/load UI controls,
  - preserving exact age day values unless the age-years field is explicitly changed,
  - preserving unknown race/gender/class ids by exposing them as `Unknown (id)` selections.

## File Format Coverage

Implemented offsets follow `file_format_docs/PCFILE_DBS.md`:

- Header fields at `0x00`, `0x02`, `0x04`
- Record size `0x01B0`
- Name at `0x000`
- Age days at `0x008`
- HP/Stamina at `0x018..0x01F`
- Load at `0x020..0x023`
- Rank/Level at `0x024..0x027`
- Stats at `0x12C..0x133`
- Skills block loaded/preserved from `0x134..0x151`
- Known spell bitset loaded/preserved from `0x188..0x193`
- Race/Gender/Class at `0x19D..0x19F`
- Portrait selector bytes are read from late-record raw bytes (`0x1A9` + `0x1AA`) for preview resolution against WPORT frames.

## Build (Windows)

Open `apps/character_roster_editor/CharacterRosterEditor.sln` in Visual Studio 2019/2022 with .NET Framework 4.8 targeting pack installed, then build and run.

Or from a Developer Command Prompt:

```powershell
msbuild apps\character_roster_editor\CharacterRosterEditor.sln /p:Configuration=Release
```
