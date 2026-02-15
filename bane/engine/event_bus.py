"""Publish/subscribe event system for decoupled communication between systems."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Event handler type: callable that takes an event dict
EventHandler = Callable[[dict[str, Any]], None]


@dataclass
class Event:
    """A game event with a type string and arbitrary data."""

    type: str
    data: dict[str, Any] = field(default_factory=dict)


# Common event type constants
EVT_PARTY_MOVED = "party.moved"
EVT_PARTY_TURNED = "party.turned"
EVT_COMBAT_START = "combat.start"
EVT_COMBAT_END = "combat.end"
EVT_COMBAT_ACTION = "combat.action"
EVT_COMBAT_DAMAGE = "combat.damage"
EVT_CHARACTER_DIED = "character.died"
EVT_CHARACTER_LEVELUP = "character.levelup"
EVT_ITEM_PICKED_UP = "item.picked_up"
EVT_ITEM_EQUIPPED = "item.equipped"
EVT_ITEM_USED = "item.used"
EVT_SPELL_CAST = "spell.cast"
EVT_DOOR_OPENED = "door.opened"
EVT_TRAP_TRIGGERED = "trap.triggered"
EVT_TRAP_DISARMED = "trap.disarmed"
EVT_DIALOGUE_START = "dialogue.start"
EVT_DIALOGUE_CHOICE = "dialogue.choice"
EVT_QUEST_FLAG_SET = "quest.flag_set"
EVT_STATE_CHANGE = "state.change"
EVT_TILE_ENTERED = "tile.entered"
EVT_ENCOUNTER = "encounter"
EVT_REST_START = "rest.start"
EVT_REST_END = "rest.end"


class EventBus:
    """Central event dispatcher using publish/subscribe pattern.

    Usage:
        bus = EventBus()
        bus.subscribe("combat.damage", on_damage)
        bus.publish(Event("combat.damage", {"target": "Goblin", "amount": 12}))
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to a specific event type."""
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to all events (useful for logging/debugging)."""
        self._global_handlers.append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe from a specific event type."""
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        # Type-specific handlers
        for handler in self._handlers.get(event.type, []):
            try:
                handler(event.data)
            except Exception:
                logger.exception("Error in event handler for '%s'", event.type)

        # Global handlers
        for handler in self._global_handlers:
            try:
                handler({"_event_type": event.type, **event.data})
            except Exception:
                logger.exception("Error in global event handler for '%s'", event.type)

    def clear(self) -> None:
        """Remove all subscribers."""
        self._handlers.clear()
        self._global_handlers.clear()
