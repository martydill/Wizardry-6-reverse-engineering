# Character Creation Editor

The shipped game data in this workspace does not store starting character stat
rules in `NEWGAME.DBS`.

After checking the binaries:

- actual party characters live in `PCFILE.DBS`
- starting stat/class/race creation tables live in `WPCMK.OVR`
- `NEWGAME.DBS` is maze/world-state data

The library for editing those starting stat tables is:

- [`bane/data/character_creation_editor.py`](/C:/Users/marty/Documents/code/bane/bane/data/character_creation_editor.py)

It edits the already-decoded `WPCMK.OVR` creation tables in place and exposes:

- male/female race stat minima
- class base-stat floors
- class availability by race
- effective starting stat preview for a race/class/gender combination

Example:

```python
from pathlib import Path

from bane.data.character_creation_editor import CharacterCreationEditor

editor = CharacterCreationEditor.from_file(Path("gamedata/WPCMK.OVR"))
print(editor.get_effective_starting_stats("male", "Human", "Fighter"))
editor.set_race_stat("male", "Human", "STR", 13)
editor.write(Path("scratch/WPCMK_patched.OVR"))
```
