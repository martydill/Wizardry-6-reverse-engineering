"""Main menu screen state."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pygame

from bane.engine.renderer import (
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    COLOR_TEXT_HIGHLIGHT,
    COLOR_UI_BG,
    COLOR_UI_BORDER,
    ORIGINAL_HEIGHT,
    ORIGINAL_WIDTH,
)
from bane.engine.state_machine import State, StateMachine

if TYPE_CHECKING:
    from bane.engine.engine import Engine


MENU_ITEMS = [
    "New Game",
    "Continue",
    "Load Game",
    "Options",
    "Quit",
]

TITLE_TEXT = "BANE ENGINE"
SUBTITLE_TEXT = "Wizardry VI: Bane of the Cosmic Forge"
VERSION_TEXT = "v0.1.0"


class MainMenuState(State):
    """Title screen and main menu."""

    def __init__(self, state_machine: StateMachine) -> None:
        super().__init__(state_machine)
        self._engine: Engine | None = None
        self._selected = 0
        self._blink_timer = 0.0

    def on_enter(self, **kwargs: Any) -> None:
        self._engine = kwargs.get("engine")

    def handle_input(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self._selected = (self._selected - 1) % len(MENU_ITEMS)
                elif event.key == pygame.K_DOWN:
                    self._selected = (self._selected + 1) % len(MENU_ITEMS)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._select_item()
                elif event.key == pygame.K_ESCAPE:
                    if self._engine:
                        self._engine.running = False

    def _select_item(self) -> None:
        item = MENU_ITEMS[self._selected]
        if item == "Quit" and self._engine:
            self._engine.running = False
        elif item == "New Game":
            from bane.ui.exploration import ExplorationState
            self.state_machine.push(ExplorationState, engine=self._engine)
        # TODO: Continue, Load Game, Options

    def update(self, dt: float) -> None:
        self._blink_timer += dt

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((10, 5, 20))

        renderer = self._engine.renderer if self._engine else None
        if renderer is None:
            return

        # Title
        renderer.draw_text_centered(TITLE_TEXT, 30, COLOR_TEXT_HIGHLIGHT)
        renderer.draw_text_centered(SUBTITLE_TEXT, 45, COLOR_TEXT)

        # Menu items
        menu_y = 90
        for i, item in enumerate(MENU_ITEMS):
            if i == self._selected:
                # Highlight selected item
                color = COLOR_TEXT_HIGHLIGHT
                prefix = "> " if int(self._blink_timer * 3) % 2 == 0 else "  "
            else:
                color = COLOR_TEXT_DIM
                prefix = "  "

            renderer.draw_text_centered(f"{prefix}{item}", menu_y + i * 14, color)

        # Version
        renderer.draw_text(VERSION_TEXT, 4, ORIGINAL_HEIGHT - 12, COLOR_TEXT_DIM)

        # Instructions
        renderer.draw_text_centered(
            "Arrow keys to navigate, Enter to select", ORIGINAL_HEIGHT - 20, COLOR_TEXT_DIM
        )
