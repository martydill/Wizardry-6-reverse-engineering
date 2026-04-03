# `PCFILE.DBS` in `WPCVW.OVR`

This note captures what the character viewer overlay (`gamedata/WPCVW.OVR`)
actually reads from each `PCFILE.DBS` character record.

Overlay mapping used here matches the existing repo convention:

- logical base: `0x4572`
- file header/prefix: `0x00F2`
- record stride: `0x01B0`

Within `WPCVW`, the per-slot record base is usually formed as:

- `slot_base = 0x43E8 + slot_index * 0x01B0`

So an instruction like `mov ax, [bx + 0x4406]` means:

- record offset `0x4406 - 0x43E8 = +0x001E`

## Confirmed field uses

### `+0x08..+0x0B` = 32-bit age counter

`WPCVW:0x54E9..0x54FE` reads:

- `[slot_base + 0x08]` as low word
- `[slot_base + 0x0A]` as high word

and divides by `0x16D` (365) before printing.

This means:

- `+0x08..+0x0B` is one 32-bit age value
- `pc_viewer.py`'s `unk_0x0A` is not separate; it is the high word of age

### `+0x18/+0x1A` = HP current / HP max

`WPCVW:0x4B70..0x4B92` passes:

- `[slot_base + 0x18]`
- `[slot_base + 0x1A]`

to the same formatter/bar routine.

So:

- `+0x18` = HP current
- `+0x1A` = HP max

### `+0x1C/+0x1E` = stamina current / stamina max

`WPCVW:0x4B95..0x4BB8` does the same for:

- `[slot_base + 0x1C]`
- `[slot_base + 0x1E]`

So:

- `+0x1C` = stamina current
- `+0x1E` = stamina max

### `+0x20/+0x22` = current load / max load

This is the biggest correction versus current Python guesses.

Evidence:

- `WPCVW:0x528C..0x5315` recomputes `[slot_base + 0x20]` by summing inventory entry costs/weights
- `WPCVW:0x50E5..0x5215` computes a percentage from `(+0x20 * 100) / +0x22`
- `WPCVW:0x5A10..0x5A6E` prints `+0x20` and `+0x22` side by side after dividing both by 10

So these are not gold / experience. They are an encumbrance-style pair:

- `+0x20` = current load
- `+0x22` = maximum load capacity

### `+0x24/+0x26` = rank / level

`WPCVW:0x55B7..0x5605` prints:

- `[slot_base + 0x26]`
- `[slot_base + 0x24]`

The label string loaded for that UI row is message `0x00C8`:

- `LVL RNK EXP MKS STR INT PIE VIT DEX SPD PER KAR HP STM CND GP CC ARMORCLASS`

So the printed order is:

- `+0x26` = `LVL`
- `+0x24` = `RNK`

That interpretation is reinforced by later spell logic:

- `WPCVW:0x6E32` increments `[slot_base + 0x26]`, consistent with level gain
- `WPCVW:0x8FCF..0x8FE7` compares `2 * spell_level` against `[slot_base + 0x24]`
  before allowing a spell to be written into the personal spellbook
- `WPCVW:0x7E58..0x7E90` derives a clamped UI value from `rank - spell_level + 1`

Current best mapping:

- `+0x24` = rank
- `+0x26` = level

### `+0x28..+0x3F` = 6 spell-school `u16/u16` pairs, but not spell-known bitmasks

`WPCVW:0x5316..0x53C6` iterates 6 records with stride 4 and prints:

- `[slot_base + 0x28 + school*4]`
- `[slot_base + 0x2A + school*4]`

So the storage shape is still:

- one `u16/u16` pair per spell school

However, a later disassembly pass through the spell-casting / spell-training
UI shows these are **not** direct spell-known bitmasks.

Key evidence:

- `WPCVW:0x845A..0x850B` saves the first word of each 4-byte school pair,
  temporarily overwrites it with `0x03E7`, calls the spell-selection UI
  (`0x7726`), then restores the original values. That only makes sense if the
  first word is a spendable / gate-checked quantity.
- `WPCVW:0x8034..0x806F` compares `[slot_base + 0x28 + school*4]` against a
  computed spell cost and refuses the action when the stored value is too low.
- `WPCVW:0x8696..0x86BF` subtracts `metadata[spell_id].cost * power` from that
  same first word after a spell is chosen.
- `WPCVW:0x857B..0x85CD` increases both words of a selected school pair
  together during the viewer's spell-growth logic.

Current best interpretation:

- first word = current spell-point pool for the school
- second word = max / base spell-point pool for the school

The viewer does print both words side by side, but the overlay code does not
use them as "known spell" ownership flags.

### `+0x188..+0x193` = 12-byte spell-known ownership block

This previously unresolved 12-byte block is now strongly implicated as the
actual spell-known bitfield structure.

Evidence:

- `WPCVW:0x82C6..0x82E8` copies 12 bytes from `slot_base + 0x188` into a local
  scratch buffer before scanning candidate spells.
- `WPCVW:0x831F..0x8376` iterates all spell ids `0..0x51` (82 total) and checks
  per-spell metadata such as school/class mask and spell level.
- for each candidate spell id, the overlay calls an external helper at
  `0x27CB` with `(local_12_byte_block, spell_id)`. Only when that helper
  returns zero does the viewer call external helper `0x279D` to add the spell
  to the copied 12-byte block.
- after selection, `WPCVW:0x8514..0x8521` calls `0x279D` again with the real
  record pointer and the chosen spell id, updating persistent character data.
- resolving the overlay thunks shows these are `WROOT` packed-bit helpers:
  - `overlay 0x27CB -> WROOT:0x28AF` = test bit at index
  - `overlay 0x279D -> WROOT:0x2881` = set/clear bit at index
- `WROOT:0x28AF` computes `byte = index >> 3` and `mask = 1 << (index & 7)`,
  then tests `buffer[byte] & mask`
- `WROOT:0x2881` uses the same byte/mask formula to update one bit

This is direct proof that:

- bit index `n` in `+0x188..+0x193` means spell id `n` is known
- there is no hidden remapping layer between spell ids and stored bit positions

So the actual `spell_id -> known/not-known` mapping is mediated by helpers
outside this overlay, and the storage they operate on is the 12-byte block at
`+0x188`.

### Spell-id metadata used by the viewer

The viewer itself does know about individual spell ids `0..81`, but through a
compact per-spell metadata table plus external helpers, not through the six
`+0x28` school words.

From the `WPCVW` side alone, the following fields are directly used for each
spell id:

- a school/class mask byte used at `0x8332`
- a spell-level byte used at `0x833D` and `0x86D4`
- a mana-cost byte used at `0x8696`
- another byte at `0x8239` used by target-selection logic

The exact storage location and encoding of that metadata table is shared /
external from the overlay's point of view.

### Practical conclusion for spell decoding

The earlier hypothesis that the six words at `+0x28..+0x3F` directly encoded
known spells was wrong.

What `WPCVW` currently proves:

- `+0x28..+0x3F` are per-school spell-point pool pairs
- `+0x188..+0x193` is the real known-spell ownership block
- the exact `spell_id -> bit position inside +0x188..+0x193` mapping is now
  solved: the position is the spell id itself, packed little-endian by bit
  within each byte

This means the next reverse-engineering target for exact spell ownership is no
longer the `+0x28` block in `WPCVW`; it is the shared helper pair and the
spell metadata table they consume.

### `+0x19C` = portrait index

This byte is not read directly in `WPCVW`, but `WBASE` uses it while drawing
party portraits.

Evidence:

- `WBASE:0x5C1C..0x5C39` walks the active character list
- for each entry it loads `byte ptr [slot_base + 0x19C]`
- it passes that byte to `WBASE:0x4F8E`
- `WBASE:0x4F8E` opens `WPORT1.*` and selects one portrait frame by dividing
  the input by `0x0E` (14 portraits per file) and using the remainder as the
  in-file portrait slot

So:

- `+0x19C` is the persisted portrait index
- it is a global portrait number across the portrait-file set, not just an
  in-file `0..13` slot

This matches observed data points such as:

- `THESUS` -> `0`
- `NOBAL` -> `3`

### `+0x40..+0xDF` = inventory entries

`WPCVW` treats `+0x40` as the start of an 8-byte-per-entry table:

- `entry_base = slot_base + 0x40 + item_index * 8`

Evidence:

- `WPCVW:0x522D..0x528B` reads an entry at `+0x40 + item*8`
- `WPCVW:0x5D3A..0x5D68`, `0x6799..0x67B8`, `0x6845..0x688D` move entries around with `rep movsw` for 8 bytes

Observed entry fields:

- `+0x00` word: item id
- `+0x02` word: per-item load contribution, stored in tenths
- `+0x04` byte: item subtype / category byte mirrored from item definitions
- `+0x05` byte: additional item category / class byte
- `+0x06` byte: quantity or charges-like byte
- `+0x07` byte: flags

Why `+0x02` is load:

- `WPCVW:0x522D..0x528B` multiplies `[entry + 0x02]` by a count
- `WPCVW:0x528C..0x5315` sums that over inventory entries into record `+0x20`
- comparing shipped characters against parsed `SCENARIO.DBS` item defs shows
  `+0x02` matches item weight in tenths for ordinary items (`50 -> 5.0`,
  `45 -> 4.5`, `30 -> 3.0`, etc.)

The viewer splits inventory into two pages using:

- `+0x1AC` = first-page count for slots `0..9`
- `+0x1AD` = second-page count for slots `10..19`

Additional partial decode from inventory logic:

- `WPCVW:0x522D..0x528B` uses `+0x04` as an index into a type table near
  overlay offset `0x00CC`
- when that table entry is `1`, the viewer multiplies `+0x02` by `+0x06`
  before adding it into current load

So:

- `+0x06` is definitely a quantity / charges-like byte for stackable entries
- `+0x07 bit 0` is a real item-state flag checked by inventory movement code
  at `WPCVW:0x673D..0x6765`

### `+0x12C..+0x133` = 8 primary stats

`WPCVW:0xA03A..0xA0B8` edits 8 consecutive bytes starting at `+0x12C`.

This confirms the current stat block mapping:

- `+0x12C..+0x133` = STR, IQ, PIE, VIT, DEX, SPD, PER, KAR

### Skill bytes confirmed by class-specific viewer logic

`WPCVW:0x5BC7` reads `[slot_base + 0x13D]`.

`WPCVW:0x5BD6` reads `[slot_base + 0x151]`.

With the existing skill block mapping (`skill_base = 0x134`), these are:

- `+0x13D` = skill index 9 = `hands_and_feet`
- `+0x151` = skill index 29 = `kirijutsu`

Those values are used by monk/ninja-specific UI code at `0x5BE2..0x5C72`.

### `+0x19D/+0x19E/+0x19F` = race / gender / class

Confirmed by:

- `WPCVW:0x54A7` -> race id from `+0x19D`
- `WPCVW:0x5464` -> gender id from `+0x19E`
- `WPCVW:0x557D`, `0x562D`, `0x83E0` -> class id from `+0x19F`

## Additional late-record metadata used by the viewer

These bytes are clearly part of the stored record and are used heavily by
inventory / UI logic:

- `+0x1A5` written by `WPCVW:0x59D9..0x59E6` from the derived block returned by `0x50AA`
- `+0x1AC` used as first inventory-page count (`WPCVW:0x52CC`)
- `+0x1AD` used as second inventory-page count (`WPCVW:0x5307`)

There are also reads from:

- `+0x1A9`
- `+0x1AA`

inside `0x50AA`, where the viewer also combines:

- `+0x20/+0x22` load percentage
- `+0x1E` stamina max

to build a 7-word derived descriptor block.

`WPCVW:0x59D9..0x59E6` then writes one derived byte from that block back to
`+0x1A5`.

So the current state is:

- `+0x1A5` is a cached viewer-derived byte, not an independent primary stat
- `+0x1A9` and `+0x1AA` are inputs to that derivation, but their exact
  gameplay meaning is still unresolved

## One more useful structural note

Several routines copy 12 bytes from:

- `slot_base + 0x188`

using `0x4570 + slot*0x1B0` as the source pointer
(`WPCVW:0x82C6..0x82E8`, `0x84C0..0x84D2`).

This block is no longer just a generic "special sub-structure":

- `+0x188..+0x193` is the persisted spell-known ownership block used by the
  spell-learning / spell-selection logic

## Practical impact for the current loader work

The following current labels in `loaders/pc_viewer.py` are wrong or incomplete:

- `unk_0x0A` should be folded into the 32-bit age field
- `unk_0x1A` is HP max
- `stamina_max_mirror` is correctly recognized as stamina max
- `Gold` / `XP` at `+0x20/+0x22` are almost certainly load / max-load, not money / experience

The viewer-backed unknown areas still worth targeting next are:

- the exact per-item meanings inside each 8-byte inventory entry
- `+0x1A5`, `+0x1A9`, `+0x1AA`
- the exact role of the still-unknown early words `+0x0C..+0x16`
