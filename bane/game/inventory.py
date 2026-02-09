"""Item and inventory management.

Handles equipment, inventory (swag bag), item identification,
equip restrictions, cursed items, and merchant buy/sell.
"""

from __future__ import annotations

import logging

from bane.data.enums import (
    EquipSlot,
    ItemFlag,
    ItemType,
    Profession,
    Race,
    Sex,
    Skill,
)
from bane.data.models import CharacterData, ItemDef

logger = logging.getLogger(__name__)

MAX_INVENTORY_SIZE = 12


class InventorySystem:
    """Manages items, equipment, and inventory operations."""

    def __init__(self, item_defs: dict[int, ItemDef] | None = None) -> None:
        self._item_defs = item_defs or {}

    def get_item_def(self, item_id: int) -> ItemDef | None:
        return self._item_defs.get(item_id)

    def can_equip(self, char: CharacterData, item: ItemDef) -> tuple[bool, str]:
        """Check if a character can equip an item."""
        if item.equip_slot is None:
            return False, "Item cannot be equipped"

        # Class restriction
        if item.class_restrictions and char.profession not in item.class_restrictions:
            return False, f"{char.profession.name} cannot equip this item"

        # Race restriction
        if item.race_restrictions and char.race not in item.race_restrictions:
            return False, f"{char.race.name} cannot equip this item"

        # Sex restriction
        if item.sex_restriction is not None and char.sex != item.sex_restriction:
            return False, f"Wrong sex to equip this item"

        return True, ""

    def equip_item(
        self, char: CharacterData, item_id: int
    ) -> tuple[bool, str]:
        """Equip an item from inventory. Returns (success, message)."""
        item = self._item_defs.get(item_id)
        if item is None:
            return False, "Unknown item"

        can, reason = self.can_equip(char, item)
        if not can:
            return False, reason

        assert item.equip_slot is not None

        # Remove from inventory
        if item_id in char.inventory:
            char.inventory.remove(item_id)

        # Unequip current item in that slot (if any, and if not cursed)
        current = char.equipment.get(item.equip_slot)
        if current is not None:
            current_def = self._item_defs.get(current)
            if current_def and (current_def.flags & ItemFlag.CURSED):
                # Put the new item back in inventory
                char.inventory.append(item_id)
                return False, "Cannot unequip cursed item!"
            char.inventory.append(current)

        char.equipment[item.equip_slot] = item_id
        return True, f"Equipped {item.name}"

    def unequip_item(
        self, char: CharacterData, slot: EquipSlot
    ) -> tuple[bool, str]:
        """Unequip an item from a slot. Returns (success, message)."""
        item_id = char.equipment.get(slot)
        if item_id is None:
            return False, "Nothing equipped in that slot"

        item = self._item_defs.get(item_id)
        if item and (item.flags & ItemFlag.CURSED):
            return False, "Cannot unequip cursed item!"

        if len(char.inventory) >= MAX_INVENTORY_SIZE:
            return False, "Inventory is full"

        char.equipment[slot] = None
        char.inventory.append(item_id)
        return True, f"Unequipped {item.name if item else 'item'}"

    def pick_up_item(
        self, char: CharacterData, item_id: int
    ) -> tuple[bool, str]:
        """Add an item to a character's inventory."""
        if len(char.inventory) >= MAX_INVENTORY_SIZE:
            return False, "Inventory is full"

        item = self._item_defs.get(item_id)
        name = item.name if item else f"Item #{item_id}"

        # Weight check
        if item:
            if char.current_weight + item.weight > char.carrying_capacity > 0:
                return False, f"Too heavy to carry {name}"
            char.current_weight += item.weight

        char.inventory.append(item_id)
        return True, f"Picked up {name}"

    def drop_item(
        self, char: CharacterData, inventory_index: int
    ) -> tuple[bool, int, str]:
        """Drop an item from inventory. Returns (success, item_id, message)."""
        if inventory_index < 0 or inventory_index >= len(char.inventory):
            return False, 0, "Invalid inventory slot"

        item_id = char.inventory.pop(inventory_index)
        item = self._item_defs.get(item_id)
        name = item.name if item else f"Item #{item_id}"

        if item:
            char.current_weight = max(0, char.current_weight - item.weight)

        return True, item_id, f"Dropped {name}"

    def identify_item(self, item_id: int, char: CharacterData | None = None) -> str:
        """Identify an item. Uses Legerdemain skill if char provided."""
        item = self._item_defs.get(item_id)
        if item is None:
            return "Unknown item"

        if item.flags & ItemFlag.IDENTIFIED:
            return item.name

        # Skill check for identification
        if char is not None:
            skill = char.skills.get(Skill.LEGERDEMAIN, 0)
            # Higher skill = better chance to identify
            import random
            if random.randint(1, 100) <= skill + 20:
                item.flags |= ItemFlag.IDENTIFIED
                return item.name

        return item.unidentified_name or "Unidentified item"

    def get_buy_price(self, item: ItemDef, haggle_skill: int = 0) -> int:
        """Calculate buy price with haggle discount."""
        base = item.value
        discount = min(50, haggle_skill // 2)  # up to 50% discount
        return max(1, int(base * (100 - discount) / 100))

    def get_sell_price(self, item: ItemDef, haggle_skill: int = 0) -> int:
        """Calculate sell price with haggle bonus."""
        base = item.value // 2  # base sell price is half
        bonus = min(30, haggle_skill // 3)  # up to 30% bonus
        return max(1, int(base * (100 + bonus) / 100))

    def get_display_name(self, item_id: int) -> str:
        """Get the display name for an item (identified or not)."""
        item = self._item_defs.get(item_id)
        if item is None:
            return f"Item #{item_id}"
        if item.flags & ItemFlag.IDENTIFIED:
            return item.name
        return item.unidentified_name or item.name
