"""Game state machine for managing screens and transitions.

States represent major game modes (main menu, exploration, combat, etc.).
Each state can handle input, update logic, and render.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pygame

logger = logging.getLogger(__name__)


class State(ABC):
    """Base class for game states."""

    def __init__(self, state_machine: StateMachine) -> None:
        self.state_machine = state_machine

    def on_enter(self, **kwargs: Any) -> None:
        """Called when entering this state."""

    def on_exit(self) -> None:
        """Called when leaving this state."""

    def on_pause(self) -> None:
        """Called when this state is pushed down the stack by another state."""

    def on_resume(self) -> None:
        """Called when this state is restored to the top of the stack."""

    @abstractmethod
    def handle_input(self, events: list[pygame.event.Event]) -> None:
        """Process input events."""

    @abstractmethod
    def update(self, dt: float) -> None:
        """Update game logic. dt is seconds since last update."""

    @abstractmethod
    def render(self, surface: pygame.Surface) -> None:
        """Render this state to the given surface."""


class StateMachine:
    """Manages a stack of game states.

    The top state receives input and renders. States below it on the stack
    are paused but preserved (e.g., exploration state stays alive under combat).
    """

    def __init__(self) -> None:
        self._stack: list[State] = []
        self._pending_operations: list[tuple[str, type[State] | None, dict[str, Any]]] = []

    @property
    def current(self) -> State | None:
        """The currently active state (top of stack)."""
        return self._stack[-1] if self._stack else None

    @property
    def stack_depth(self) -> int:
        return len(self._stack)

    def push(self, state_class: type[State], **kwargs: Any) -> None:
        """Push a new state onto the stack."""
        self._pending_operations.append(("push", state_class, kwargs))

    def pop(self) -> None:
        """Pop the current state off the stack."""
        self._pending_operations.append(("pop", None, {}))

    def switch(self, state_class: type[State], **kwargs: Any) -> None:
        """Replace the current state with a new one."""
        self._pending_operations.append(("switch", state_class, kwargs))

    def clear(self) -> None:
        """Clear all states."""
        self._pending_operations.append(("clear", None, {}))

    def process_pending(self) -> None:
        """Process any pending state changes. Call this once per frame."""
        while self._pending_operations:
            op, state_class, kwargs = self._pending_operations.pop(0)

            if op == "push":
                assert state_class is not None
                if self._stack:
                    self._stack[-1].on_pause()
                new_state = state_class(self)
                self._stack.append(new_state)
                new_state.on_enter(**kwargs)
                logger.info("Pushed state: %s", state_class.__name__)

            elif op == "pop":
                if self._stack:
                    old = self._stack.pop()
                    old.on_exit()
                    logger.info("Popped state: %s", type(old).__name__)
                    if self._stack:
                        self._stack[-1].on_resume()

            elif op == "switch":
                assert state_class is not None
                if self._stack:
                    old = self._stack.pop()
                    old.on_exit()
                new_state = state_class(self)
                self._stack.append(new_state)
                new_state.on_enter(**kwargs)
                logger.info("Switched to state: %s", state_class.__name__)

            elif op == "clear":
                while self._stack:
                    state = self._stack.pop()
                    state.on_exit()
                logger.info("Cleared all states")

    def handle_input(self, events: list[pygame.event.Event]) -> None:
        if self._stack:
            self._stack[-1].handle_input(events)

    def update(self, dt: float) -> None:
        self.process_pending()
        if self._stack:
            self._stack[-1].update(dt)

    def render(self, surface: pygame.Surface) -> None:
        if self._stack:
            self._stack[-1].render(surface)
