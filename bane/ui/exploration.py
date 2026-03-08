"""Exploration state — first-person dungeon crawling."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pygame

from bane.data.enums import Direction, TileSpecial
from bane.data.map_loader import DungeonMap, MapPosition
from bane.engine.renderer import (
    COLOR_HP_BAR,
    COLOR_SP_BAR,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    COLOR_TEXT_HIGHLIGHT,
    ORIGINAL_HEIGHT,
    ORIGINAL_WIDTH,
    VIEWPORT_H,
    VIEWPORT_W,
    VIEWPORT_X,
    VIEWPORT_Y,
)
from bane.engine.state_machine import State, StateMachine

if TYPE_CHECKING:
    from bane.engine.engine import Engine


class ExplorationState(State):
    """First-person dungeon exploration mode."""

    def __init__(self, state_machine: StateMachine) -> None:
        super().__init__(state_machine)
        self._engine: Engine | None = None
        self._position = MapPosition(level=11, x=131, y=141, facing=Direction.NORTH)
        self._message_log: list[str] = []
        self._message_timer = 0.0

    def on_enter(self, **kwargs: Any) -> None:
        self._engine = kwargs.get("engine")
        self._add_message("You enter the dungeon...")

        # Load save game position if available
        if self._engine:
            save = self._engine.resources.get_save()
            if save:
                self._position = MapPosition(
                    level=save.current_level,
                    x=save.position_x,
                    y=save.position_y,
                    facing=save.facing,
                )

    def _add_message(self, text: str) -> None:
        self._message_log.append(text)
        if len(self._message_log) > 5:
            self._message_log.pop(0)
        self._message_timer = 3.0

    def handle_input(self, events: list[pygame.event.Event]) -> None:
        if self._engine is None:
            return

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP or event.key == pygame.K_w:
                    self._try_move(self._position)
                elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                    backward = self._position.turn_around()
                    self._try_move(backward)
                elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                    self._position = self._position.turn_left()
                    self._add_message(f"Facing {self._position.facing.name}")
                elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                    self._position = self._position.turn_right()
                    self._add_message(f"Facing {self._position.facing.name}")
                elif event.key == pygame.K_q:
                    # Strafe left
                    strafe = MapPosition(
                        self._position.level,
                        self._position.x,
                        self._position.y,
                        self._position.facing.turn_left(),
                    )
                    new_pos = self._try_move_silent(strafe)
                    if new_pos:
                        self._position = MapPosition(
                            new_pos.level, new_pos.x, new_pos.y,
                            self._position.facing,
                        )
                elif event.key == pygame.K_e:
                    # Strafe right
                    strafe = MapPosition(
                        self._position.level,
                        self._position.x,
                        self._position.y,
                        self._position.facing.turn_right(),
                    )
                    new_pos = self._try_move_silent(strafe)
                    if new_pos:
                        self._position = MapPosition(
                            new_pos.level, new_pos.x, new_pos.y,
                            self._position.facing,
                        )
                elif event.key == pygame.K_m:
                    self._add_message("Automap (TODO)")
                elif event.key == pygame.K_c:
                    self._add_message("Camp (TODO)")
                elif event.key == pygame.K_ESCAPE:
                    self.state_machine.pop()

    def _get_dir_vec(self, facing: Direction) -> tuple[int, int]:
        if facing == Direction.NORTH: return 0, -1
        if facing == Direction.SOUTH: return 0, 1
        if facing == Direction.EAST: return 1, 0
        if facing == Direction.WEST: return -1, 0
        return 0, -1

    def _can_move(self, pos: MapPosition) -> bool:
        if not self._engine: return False
        maze = self._engine.renderer.renderer_3d.maze
        dx, dy = self._get_dir_vec(pos.facing)
        
        # Check if maze map is loaded
        if pos.level not in maze.maps:
            maze.load_map(pos.level)
            
        wall = maze.get_wall(pos.level, pos.x, pos.y, dx, dy)
        return wall == 0

    def _try_move(self, pos: MapPosition) -> None:
        """Try to move forward from the given position."""
        if self._can_move(pos):
            new_pos = pos.forward()
            self._position = MapPosition(
                new_pos.level, new_pos.x, new_pos.y, self._position.facing
            )
            # self._check_tile_effects(dungeon) # Disabled until SCENARIO is loaded
        else:
            self._add_message("You can't go that way.")

    def _try_move_silent(self, pos: MapPosition) -> MapPosition | None:
        """Try to move without messages. Returns new pos or None."""
        if self._can_move(pos):
            return pos.forward()
        return None

    def update(self, dt: float) -> None:
        if self._message_timer > 0:
            self._message_timer -= dt

    def render(self, surface: pygame.Surface) -> None:
        if self._engine is None:
            return

        renderer = self._engine.renderer
        dungeon = self._engine.resources.dungeon_map

        surface.fill((10, 5, 15))

        # Render dungeon viewport
        renderer.render_dungeon_view(dungeon, self._position)

        # Viewport border
        renderer.draw_rect(
            VIEWPORT_X - 1, VIEWPORT_Y - 1,
            VIEWPORT_W + 2, VIEWPORT_H + 2,
            (80, 60, 100), filled=False,
        )

        # Compass
        compass_x = VIEWPORT_X + VIEWPORT_W + 8
        compass_y = VIEWPORT_Y
        renderer.draw_text("Compass", compass_x, compass_y, COLOR_TEXT_DIM)
        facing_str = self._position.facing.name
        renderer.draw_text(facing_str, compass_x, compass_y + 12, COLOR_TEXT_HIGHLIGHT)

        # Position info
        renderer.draw_text(
            f"L{self._position.level} ({self._position.x},{self._position.y})",
            compass_x, compass_y + 28, COLOR_TEXT_DIM,
        )

        # Party status (right side)
        party_x = VIEWPORT_X + VIEWPORT_W + 8
        party_y = VIEWPORT_Y + 50
        chars = self._engine.resources.get_characters()
        for i, char in enumerate(chars[:6]):
            y = party_y + i * 16
            name_color = COLOR_TEXT if char.is_alive() else (150, 40, 40)
            renderer.draw_text(char.name[:8], party_x, y, name_color)
            # HP bar
            renderer.draw_bar(party_x + 60, y + 1, 30, 5, char.hp_current, char.hp_max, COLOR_HP_BAR)
            # SP bar
            if char.sp_max > 0:
                renderer.draw_bar(party_x + 60, y + 7, 30, 3, char.sp_current, char.sp_max, COLOR_SP_BAR)

        # Message log (bottom)
        msg_y = VIEWPORT_Y + VIEWPORT_H + 8
        renderer.draw_rect(4, msg_y - 2, ORIGINAL_WIDTH - 8, 70, (15, 10, 20))
        renderer.draw_rect(4, msg_y - 2, ORIGINAL_WIDTH - 8, 70, (60, 50, 80), filled=False)
        for i, msg in enumerate(self._message_log[-5:]):
            alpha = 1.0 if i == len(self._message_log[-5:]) - 1 else 0.6
            color = COLOR_TEXT if alpha > 0.8 else COLOR_TEXT_DIM
            renderer.draw_text(msg[:50], 8, msg_y + i * 12, color)

        # Controls hint
        renderer.draw_text(
            "WASD/Arrows:Move  Q/E:Strafe  M:Map  C:Camp  ESC:Back",
            4, ORIGINAL_HEIGHT - 10, COLOR_TEXT_DIM,
        )
