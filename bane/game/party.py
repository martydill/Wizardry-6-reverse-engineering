"""Party management — managing the group of up to 6 characters."""

from __future__ import annotations

import logging

from bane.data.enums import Condition
from bane.data.models import CharacterData

logger = logging.getLogger(__name__)

MAX_PARTY_SIZE = 6


class Party:
    """Manages the player's party of up to 6 characters.

    Provides:
    - Add/remove/reorder members
    - Party-wide queries (all alive, all active, etc.)
    - Gold pool management
    - Formation tracking
    """

    def __init__(self) -> None:
        self._members: list[CharacterData] = []
        self._gold: int = 0

    @property
    def members(self) -> list[CharacterData]:
        return list(self._members)

    @property
    def size(self) -> int:
        return len(self._members)

    @property
    def is_full(self) -> bool:
        return len(self._members) >= MAX_PARTY_SIZE

    @property
    def gold(self) -> int:
        return self._gold

    @gold.setter
    def gold(self, value: int) -> None:
        self._gold = max(0, value)

    def add_member(self, char: CharacterData) -> bool:
        """Add a character to the party. Returns False if party is full."""
        if self.is_full:
            return False
        self._members.append(char)
        logger.info("Added %s to party (size: %d)", char.name, len(self._members))
        return True

    def remove_member(self, index: int) -> CharacterData | None:
        """Remove and return the character at the given index."""
        if 0 <= index < len(self._members):
            char = self._members.pop(index)
            logger.info("Removed %s from party", char.name)
            return char
        return None

    def swap_members(self, i: int, j: int) -> None:
        """Swap two party members' positions."""
        if 0 <= i < len(self._members) and 0 <= j < len(self._members):
            self._members[i], self._members[j] = self._members[j], self._members[i]

    def get_member(self, index: int) -> CharacterData | None:
        if 0 <= index < len(self._members):
            return self._members[index]
        return None

    def get_alive_members(self) -> list[CharacterData]:
        """Get all living party members."""
        return [m for m in self._members if m.is_alive()]

    def get_active_members(self) -> list[CharacterData]:
        """Get all members who can act (not dead, stoned, paralyzed, asleep)."""
        return [m for m in self._members if m.is_active()]

    def get_front_row(self) -> list[CharacterData]:
        """First 3 members are front row (take melee hits)."""
        return self._members[:3]

    def get_back_row(self) -> list[CharacterData]:
        """Last 3 members are back row (ranged/magic)."""
        return self._members[3:]

    def is_wiped(self) -> bool:
        """True if all party members are dead."""
        return all(not m.is_alive() for m in self._members) if self._members else True

    def heal_all(self) -> None:
        """Restore all party members to full HP/STA/SP (for resting)."""
        for m in self._members:
            if m.is_alive():
                m.hp_current = m.hp_max
                m.stamina_current = m.stamina_max
                m.sp_current = m.sp_max

    def distribute_xp(self, total_xp: int) -> dict[str, int]:
        """Distribute XP evenly among alive party members. Returns per-character XP."""
        alive = self.get_alive_members()
        if not alive:
            return {}
        per_member = total_xp // len(alive)
        result = {}
        for m in alive:
            m.experience += per_member
            result[m.name] = per_member
        return result

    def distribute_gold(self, amount: int) -> None:
        """Add gold to the party pool."""
        self._gold += amount
