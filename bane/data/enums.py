"""Enumerations for all Wizardry 6 game constants.

These map directly to the values stored in the original binary data files.
"""

from __future__ import annotations

from enum import IntEnum, IntFlag


# ---------------------------------------------------------------------------
# Races (11 total)
# ---------------------------------------------------------------------------
class Race(IntEnum):
    HUMAN = 0
    ELF = 1
    DWARF = 2
    GNOME = 3
    HOBBIT = 4
    FAERIE = 5
    LIZARDMAN = 6
    DRACON = 7
    FELPURR = 8
    RAWULF = 9
    MOOK = 10


# ---------------------------------------------------------------------------
# Classes / Professions (14 total)
# ---------------------------------------------------------------------------
class Profession(IntEnum):
    FIGHTER = 0
    MAGE = 1
    PRIEST = 2
    THIEF = 3
    RANGER = 4
    ALCHEMIST = 5
    BARD = 6
    PSIONIC = 7
    VALKYRIE = 8
    BISHOP = 9
    LORD = 10
    SAMURAI = 11
    MONK = 12
    NINJA = 13


# ---------------------------------------------------------------------------
# Sex
# ---------------------------------------------------------------------------
class Sex(IntEnum):
    MALE = 0
    FEMALE = 1


# ---------------------------------------------------------------------------
# Ability Scores (7 core stats)
# ---------------------------------------------------------------------------
class Ability(IntEnum):
    STRENGTH = 0
    INTELLIGENCE = 1
    PIETY = 2
    VITALITY = 3
    DEXTERITY = 4
    SPEED = 5
    PERSONALITY = 6


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------
class Skill(IntEnum):
    # Weapon skills (improve through use)
    SWORD = 0
    AXE = 1
    MACE_AND_FLAIL = 2
    POLE_AND_STAFF = 3
    THROWING_AND_SLING = 4
    BOW = 5
    SHIELD = 6
    # Physical skills (improve through use)
    SCOUTING = 7
    SWIMMING = 8
    CLIMBING = 9
    SKULDUGGERY = 10  # lockpicking, trap disarm
    MAPPING = 11
    MUSIC = 12
    # Magic skills (level-up allocation only)
    ORATORY = 13
    ALCHEMY = 14
    THEOLOGY = 15
    THEOSOPHY = 16
    THAUMATURGY = 17
    # Combat skills
    NINJUTSU = 18  # level-up only
    KIRIJUTSU = 19  # level-up only, critical strike
    ARTIFACTS = 20
    MYTHOLOGY = 21
    COMMUNICATION = 22
    LEGERDEMAIN = 23


# ---------------------------------------------------------------------------
# Spell Schools
# ---------------------------------------------------------------------------
class SpellSchool(IntEnum):
    MAGE = 0
    PRIEST = 1
    ALCHEMIST = 2
    PSIONIC = 3


# Skill thresholds for unlocking spell levels
SPELL_LEVEL_THRESHOLDS = {
    1: 0,
    2: 18,
    3: 36,
    4: 54,
    5: 72,
    6: 90,
    7: 98,
}


# ---------------------------------------------------------------------------
# Attack Modes / Damage Types (9 types)
# ---------------------------------------------------------------------------
class AttackMode(IntEnum):
    PHYSICAL = 0
    FIRE = 1
    COLD = 2
    ELECTRIC = 3
    MENTAL = 4
    DIVINE = 5
    MAGIC = 6
    STONE = 7
    SPECIAL = 8


# ---------------------------------------------------------------------------
# Equipment Slots
# ---------------------------------------------------------------------------
class EquipSlot(IntEnum):
    MAIN_HAND = 0
    OFF_HAND = 1  # shield or secondary weapon
    HEAD = 2
    TORSO = 3
    LEGS = 4
    FEET = 5
    HANDS = 6
    ACCESSORY = 7


# ---------------------------------------------------------------------------
# Item Types
# ---------------------------------------------------------------------------
class ItemType(IntEnum):
    WEAPON = 0
    ARMOR = 1
    SHIELD = 2
    HELMET = 3
    GLOVES = 4
    BOOTS = 5
    CLOAK = 6
    ACCESSORY = 7
    SCROLL = 8
    POTION = 9
    WAND = 10
    MISC = 11
    QUEST = 12
    AMMO = 13
    INSTRUMENT = 14
    POWDER = 15
    BOOK = 16
    FOOD = 17


# ---------------------------------------------------------------------------
# Item Flags
# ---------------------------------------------------------------------------
class ItemFlag(IntFlag):
    NONE = 0
    IDENTIFIED = 1 << 0
    EQUIPPED = 1 << 1
    CURSED = 1 << 2
    QUEST_ITEM = 1 << 3
    TWO_HANDED = 1 << 4
    USABLE = 1 << 5
    CASTABLE = 1 << 6
    STACKABLE = 1 << 7


# ---------------------------------------------------------------------------
# Status Conditions
# ---------------------------------------------------------------------------
class Condition(IntFlag):
    NONE = 0
    POISONED = 1 << 0
    DISEASED = 1 << 1
    PARALYZED = 1 << 2
    STONED = 1 << 3  # petrified
    DEAD = 1 << 4
    ASLEEP = 1 << 5
    AFRAID = 1 << 6
    SILENCED = 1 << 7
    BLINDED = 1 << 8
    NAUSEA = 1 << 9
    INSANE = 1 << 10
    IRRITATED = 1 << 11
    HEXED = 1 << 12
    LEVEL_DRAINED = 1 << 13


# ---------------------------------------------------------------------------
# Wall Types (2-bit encoding per wall in map tiles)
# ---------------------------------------------------------------------------
class WallType(IntEnum):
    NONE = 0       # open passage
    WALL = 1       # solid wall
    DOOR = 2       # door (may be locked)
    SECRET = 3     # secret door (requires Scouting to detect)


# ---------------------------------------------------------------------------
# Facing Direction
# ---------------------------------------------------------------------------
class Direction(IntEnum):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3

    def turn_left(self) -> Direction:
        return Direction((self.value - 1) % 4)

    def turn_right(self) -> Direction:
        return Direction((self.value + 1) % 4)

    def reverse(self) -> Direction:
        return Direction((self.value + 2) % 4)

    @property
    def dx(self) -> int:
        """X offset for moving in this direction."""
        return (0, 1, 0, -1)[self.value]

    @property
    def dy(self) -> int:
        """Y offset for moving in this direction."""
        return (-1, 0, 1, 0)[self.value]


# ---------------------------------------------------------------------------
# Special Tile Types
# ---------------------------------------------------------------------------
class TileSpecial(IntEnum):
    NONE = 0
    STAIRS_UP = 1
    STAIRS_DOWN = 2
    TELEPORTER = 3
    SPINNER = 4
    DARK_ZONE = 5
    ANTI_MAGIC = 6
    DAMAGE_FLOOR = 7
    ENCOUNTER_ZONE = 8
    PIT = 9
    CHUTE = 10


# ---------------------------------------------------------------------------
# Game States
# ---------------------------------------------------------------------------
class GameState(IntEnum):
    MAIN_MENU = 0
    CHARACTER_CREATION = 1
    EXPLORATION = 2
    COMBAT = 3
    CAMP = 4
    DIALOGUE = 5
    MERCHANT = 6
    CHARACTER_SHEET = 7
    SPELL_BOOK = 8
    AUTOMAP = 9
    GAME_OVER = 10
    VICTORY = 11


# ---------------------------------------------------------------------------
# Spell Target Types
# ---------------------------------------------------------------------------
class SpellTarget(IntEnum):
    SELF = 0
    SINGLE_ALLY = 1
    ALL_ALLIES = 2
    SINGLE_ENEMY = 3
    ENEMY_GROUP = 4
    ALL_ENEMIES = 5


# ---------------------------------------------------------------------------
# Combat Action Types
# ---------------------------------------------------------------------------
class CombatAction(IntEnum):
    ATTACK = 0
    PARRY = 1  # defend
    CAST_SPELL = 2
    USE_ITEM = 3
    FLEE = 4
    HIDE = 5
    EQUIP = 6
    GUARD = 7
