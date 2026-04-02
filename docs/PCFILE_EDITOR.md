# PCFILE Editor

The new editor library for party characters is:

- [`bane/data/pcfile_editor.py`](/C:/Users/marty/Documents/code/bane/bane/data/pcfile_editor.py)

This is an in-place patch editor for the shipped
[`gamedata/PCFILE.DBS`](/C:/Users/marty/Documents/code/bane/gamedata/PCFILE.DBS).

## Scope

It currently exposes only fields that are stable from the sample file layout:

- character name
- level
- HP
- gold
- experience
- raw age word
- contiguous 8-byte stat block at record offset `0x12C`

The first six stat bytes are high-confidence:

- `strength`
- `intelligence`
- `piety`
- `vitality`
- `dexterity`
- `speed`

The final two stat bytes are still provisional in the current RE state, so the
API labels them conservatively as:

- `luck_or_personality`
- `unknown_stat_8`

## Example

```python
from pathlib import Path

from bane.data.pcfile_editor import PCFileEditor

editor = PCFileEditor.from_file(Path("gamedata/PCFILE.DBS"))
thesus = editor.find_by_name("THESUS")
thesus.level = 10
thesus.hp = 150
thesus.gold = 999
thesus.set_stat("str", 20)
editor.write(Path("scratch/PCFILE_patched.DBS"))
```
