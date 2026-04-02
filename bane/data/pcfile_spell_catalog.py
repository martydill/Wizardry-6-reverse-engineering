"""Spell catalog helpers for `PCFILE.DBS`.

The `WPCVW` spell viewer path now supports two strong conclusions:

- the 12-byte block at `PCFILE + 0x188` is a packed known-spell bitset
- bit index `n` in that block corresponds directly to spell id `n`

This module provides a local spell-id catalog so `PCFILE.DBS` tooling can name
those bits without relying on the still-incomplete `SCENARIO.DBS` spell parser.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PCFileSpellDef:
    id: int
    name: str
    sphere: str
    level: int
    mana: int


SPELL_DEFS: tuple[PCFileSpellDef, ...] = (
    PCFileSpellDef(0, "Energy Blast", "fire", 1, 2),
    PCFileSpellDef(1, "Blinding Flash", "fire", 2, 3),
    PCFileSpellDef(2, "Fireball", "fire", 3, 6),
    PCFileSpellDef(3, "Fire Shield", "fire", 3, 8),
    PCFileSpellDef(4, "Fire Bomb", "fire", 4, 8),
    PCFileSpellDef(5, "Lightning", "fire", 5, 8),
    PCFileSpellDef(6, "Prismic Missile", "fire", 5, 9),
    PCFileSpellDef(7, "Firestorm", "fire", 6, 12),
    PCFileSpellDef(8, "Nuclear Blast", "fire", 7, 16),
    PCFileSpellDef(9, "Chilling Touch", "water", 1, 2),
    PCFileSpellDef(10, "Stamina", "water", 1, 2),
    PCFileSpellDef(11, "Terror", "water", 1, 3),
    PCFileSpellDef(12, "Weaken", "water", 2, 4),
    PCFileSpellDef(13, "Slow", "water", 2, 4),
    PCFileSpellDef(14, "Haste", "water", 3, 5),
    PCFileSpellDef(15, "Cure Paralysis", "water", 3, 6),
    PCFileSpellDef(16, "Ice Shield", "water", 3, 8),
    PCFileSpellDef(17, "Iceball", "water", 4, 8),
    PCFileSpellDef(18, "Paralyze", "water", 4, 5),
    PCFileSpellDef(19, "Deep Freeze", "water", 5, 6),
    PCFileSpellDef(20, "Poison", "air", 1, 2),
    PCFileSpellDef(21, "Missile Shield", "air", 2, 5),
    PCFileSpellDef(22, "Stink Bomb", "air", 3, 4),
    PCFileSpellDef(23, "Air Pocket", "air", 3, 8),
    PCFileSpellDef(24, "Silence", "air", 3, 4),
    PCFileSpellDef(25, "Poison Gas", "air", 4, 7),
    PCFileSpellDef(26, "Cure Poison", "air", 4, 8),
    PCFileSpellDef(27, "Whirlwind", "air", 4, 8),
    PCFileSpellDef(28, "Purify Air", "air", 5, 10),
    PCFileSpellDef(29, "Deadly Poison", "air", 5, 8),
    PCFileSpellDef(30, "Levitate", "air", 5, 12),
    PCFileSpellDef(31, "Toxic Vapors", "air", 6, 8),
    PCFileSpellDef(32, "Noxious Fumes", "air", 6, 10),
    PCFileSpellDef(33, "Asphyxiation", "air", 6, 12),
    PCFileSpellDef(34, "Deadly Air", "air", 7, 16),
    PCFileSpellDef(35, "Acid Splash", "earth", 1, 2),
    PCFileSpellDef(36, "Itching Skin", "earth", 1, 2),
    PCFileSpellDef(37, "Armor Shield", "earth", 1, 2),
    PCFileSpellDef(38, "Direction", "earth", 1, 3),
    PCFileSpellDef(39, "Knock-knock", "earth", 2, 6),
    PCFileSpellDef(40, "Blades", "earth", 3, 6),
    PCFileSpellDef(41, "Armorplate", "earth", 3, 6),
    PCFileSpellDef(42, "Web", "earth", 3, 7),
    PCFileSpellDef(43, "Acid Bomb", "earth", 4, 8),
    PCFileSpellDef(44, "Armormelt", "earth", 4, 8),
    PCFileSpellDef(45, "Create Life", "earth", 5, 10),
    PCFileSpellDef(46, "Cure Stone", "earth", 6, 18),
    PCFileSpellDef(47, "Mental Attack", "mental", 1, 3),
    PCFileSpellDef(48, "Sleep", "mental", 1, 3),
    PCFileSpellDef(49, "Bless", "mental", 1, 4),
    PCFileSpellDef(50, "Charm", "mental", 1, 5),
    PCFileSpellDef(51, "Cure Lesser Cnd", "mental", 2, 4),
    PCFileSpellDef(52, "Divine Trap", "mental", 2, 4),
    PCFileSpellDef(53, "Detect Secret", "mental", 2, 5),
    PCFileSpellDef(54, "Identify", "mental", 2, 8),
    PCFileSpellDef(55, "Hold Monsters", "mental", 3, 6),
    PCFileSpellDef(56, "Mindread", "mental", 3, 8),
    PCFileSpellDef(57, "Sane Mind", "mental", 3, 10),
    PCFileSpellDef(58, "Psionic Blast", "mental", 4, 8),
    PCFileSpellDef(59, "Illusion", "mental", 4, 10),
    PCFileSpellDef(60, "Wizard Eye", "mental", 4, 10),
    PCFileSpellDef(61, "Death", "mental", 5, 10),
    PCFileSpellDef(62, "Locate Object", "mental", 6, 8),
    PCFileSpellDef(63, "Mind Flay", "mental", 7, 18),
    PCFileSpellDef(64, "Heal Wounds", "magic", 1, 4),
    PCFileSpellDef(65, "Make Wounds", "magic", 1, 3),
    PCFileSpellDef(66, "Magic Missile", "magic", 2, 4),
    PCFileSpellDef(67, "Dispel Undead", "magic", 2, 7),
    PCFileSpellDef(68, "Enchanted Blade", "magic", 2, 4),
    PCFileSpellDef(69, "Blink", "magic", 3, 7),
    PCFileSpellDef(70, "Magic Screen", "magic", 4, 8),
    PCFileSpellDef(71, "Conjuration", "magic", 4, 10),
    PCFileSpellDef(72, "Anti-magic", "magic", 5, 7),
    PCFileSpellDef(73, "Remove Curse", "magic", 5, 10),
    PCFileSpellDef(74, "Lifesteal", "magic", 6, 12),
    PCFileSpellDef(75, "Astral Gate", "magic", 6, 8),
    PCFileSpellDef(76, "Word Of Death", "magic", 7, 18),
    PCFileSpellDef(77, "Resurrection", "magic", 7, 20),
    PCFileSpellDef(78, "Death Wish", "magic", 7, 20),
    PCFileSpellDef(79, "Holy Water", "magic", 0, 0),
    PCFileSpellDef(80, "Helpfood", "magic", 0, 0),
    PCFileSpellDef(81, "Magicfood", "magic", 0, 0),
)


SPELL_DEF_BY_ID: dict[int, PCFileSpellDef] = {spell.id: spell for spell in SPELL_DEFS}
SPELL_IDS_BY_SPHERE: dict[str, list[int]] = {}
for _spell in SPELL_DEFS:
    SPELL_IDS_BY_SPHERE.setdefault(_spell.sphere, []).append(_spell.id)


def spell_def_by_id(spell_id: int) -> PCFileSpellDef | None:
    return SPELL_DEF_BY_ID.get(spell_id)


def spell_name_by_id(spell_id: int) -> str | None:
    spell = spell_def_by_id(spell_id)
    return spell.name if spell else None


def known_spell_ids_from_block(data: bytes | bytearray, offset: int = 0x188, size: int = 12) -> list[int]:
    """Decode the packed known-spell bitset from a `PCFILE.DBS` record."""
    block = data[offset:offset + size]
    out: list[int] = []
    for spell_id in range(min(len(SPELL_DEFS), len(block) * 8)):
        byte_index = spell_id >> 3
        bit_mask = 1 << (spell_id & 7)
        if block[byte_index] & bit_mask:
            out.append(spell_id)
    return out
