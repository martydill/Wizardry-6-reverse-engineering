"""Rendering system for the Bane Engine.

Provides:
- 2D sprite/texture rendering
- First-person dungeon viewport rendering
- Text rendering
- UI primitive drawing
- Resolution scaling (original 320x200 → modern resolutions)
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

import pygame

from bane.data.enums import Direction, WallType
from bane.data.map_loader import DungeonMap, MapPosition
from bane.data.sprite_decoder import Sprite
from bane.engine.config import ORIGINAL_HEIGHT, ORIGINAL_WIDTH

if TYPE_CHECKING:
    from bane.data.models import TileData

logger = logging.getLogger(__name__)

# Dungeon viewport dimensions (in original resolution coordinates)
VIEWPORT_X = 8
VIEWPORT_Y = 8
VIEWPORT_W = 176
VIEWPORT_H = 112

# Colors
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (128, 128, 128)
COLOR_DARK_GRAY = (64, 64, 64)
COLOR_WALL = (100, 80, 60)
COLOR_DOOR = (140, 100, 50)
COLOR_FLOOR = (40, 40, 50)
COLOR_CEILING = (30, 30, 40)
COLOR_SECRET = (80, 80, 100)
COLOR_UI_BG = (20, 15, 25)
COLOR_UI_BORDER = (100, 80, 120)
COLOR_HP_BAR = (200, 40, 40)
COLOR_SP_BAR = (40, 80, 200)
COLOR_TEXT = (220, 210, 190)
COLOR_TEXT_HIGHLIGHT = (255, 255, 200)
COLOR_TEXT_DIM = (120, 110, 100)


class Renderer:
    """Main rendering system.

    Renders to an internal surface at the original 320x200 resolution,
    then scales up to the window size for pixel-perfect display.
    """

    def __init__(self, window_surface: pygame.Surface, scale: int = 3) -> None:
        self.window = window_surface
        self.scale = scale
        # Internal render target at original resolution
        self.internal = pygame.Surface((ORIGINAL_WIDTH, ORIGINAL_HEIGHT))
        self._font: pygame.font.Font | None = None
        self._sprite_cache: dict[int, pygame.Surface] = {}

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, 8)  # Small bitmap-style font
        return self._font

    def begin_frame(self) -> None:
        """Clear the internal surface for a new frame."""
        self.internal.fill(COLOR_BLACK)

    def end_frame(self) -> None:
        """Scale internal surface to window and flip."""
        scaled = pygame.transform.scale(
            self.internal,
            (ORIGINAL_WIDTH * self.scale, ORIGINAL_HEIGHT * self.scale),
        )
        # Center on window
        wx, wy = self.window.get_size()
        sx, sy = scaled.get_size()
        x = (wx - sx) // 2
        y = (wy - sy) // 2
        self.window.fill(COLOR_BLACK)
        self.window.blit(scaled, (x, y))
        pygame.display.flip()

    # ----- Sprite rendering -----

    def sprite_to_surface(self, sprite: Sprite) -> pygame.Surface:
        """Convert a Sprite to a pygame Surface."""
        surf = pygame.Surface((sprite.width, sprite.height), pygame.SRCALPHA)
        rgba_data = sprite.to_rgba_bytes()
        # Create surface from raw RGBA data
        temp = pygame.image.frombuffer(rgba_data, (sprite.width, sprite.height), "RGBA")
        surf.blit(temp, (0, 0))
        return surf

    def draw_sprite(self, sprite: Sprite, x: int, y: int) -> None:
        """Draw a sprite at (x, y) on the internal surface."""
        surf = self.sprite_to_surface(sprite)
        self.internal.blit(surf, (x, y))

    # ----- Text rendering -----

    def draw_text(
        self,
        text: str,
        x: int,
        y: int,
        color: tuple[int, int, int] = COLOR_TEXT,
    ) -> None:
        """Draw text at (x, y) on the internal surface."""
        rendered = self.font.render(text, False, color)
        self.internal.blit(rendered, (x, y))

    def draw_text_centered(
        self,
        text: str,
        y: int,
        color: tuple[int, int, int] = COLOR_TEXT,
    ) -> None:
        """Draw horizontally centered text."""
        rendered = self.font.render(text, False, color)
        x = (ORIGINAL_WIDTH - rendered.get_width()) // 2
        self.internal.blit(rendered, (x, y))

    # ----- UI primitives -----

    def draw_rect(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        color: tuple[int, int, int],
        filled: bool = True,
    ) -> None:
        if filled:
            pygame.draw.rect(self.internal, color, (x, y, w, h))
        else:
            pygame.draw.rect(self.internal, color, (x, y, w, h), 1)

    def draw_hline(
        self, x: int, y: int, length: int, color: tuple[int, int, int]
    ) -> None:
        pygame.draw.line(self.internal, color, (x, y), (x + length, y))

    def draw_vline(
        self, x: int, y: int, length: int, color: tuple[int, int, int]
    ) -> None:
        pygame.draw.line(self.internal, color, (x, y), (x, y + length))

    def draw_panel(
        self, x: int, y: int, w: int, h: int, bg: tuple[int, int, int] = COLOR_UI_BG
    ) -> None:
        """Draw a UI panel with border."""
        self.draw_rect(x, y, w, h, bg)
        self.draw_rect(x, y, w, h, COLOR_UI_BORDER, filled=False)

    def draw_bar(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        current: int,
        maximum: int,
        color: tuple[int, int, int],
    ) -> None:
        """Draw a progress/health bar."""
        self.draw_rect(x, y, w, h, COLOR_DARK_GRAY)
        if maximum > 0:
            fill_w = max(1, int(w * current / maximum))
            self.draw_rect(x, y, fill_w, h, color)

    # ----- First-person dungeon rendering -----

    def render_dungeon_view(
        self,
        dungeon_map: DungeonMap,
        position: MapPosition,
    ) -> None:
        """Render the first-person dungeon viewport.

        Uses a simplified pseudo-3D approach for grid-based dungeons:
        - Draw walls receding into the distance
        - Layer-by-layer from far to near
        - Each layer has left wall, right wall, front wall, floor, ceiling
        """
        # Draw floor and ceiling base
        self.draw_rect(
            VIEWPORT_X, VIEWPORT_Y,
            VIEWPORT_W, VIEWPORT_H // 2,
            COLOR_CEILING,
        )
        self.draw_rect(
            VIEWPORT_X, VIEWPORT_Y + VIEWPORT_H // 2,
            VIEWPORT_W, VIEWPORT_H // 2,
            COLOR_FLOOR,
        )

        max_depth = 4
        cells = dungeon_map.get_view_cells(position, max_depth)

        # Render from back to front
        for depth, cell_pos in reversed(list(enumerate(cells))):
            tile = dungeon_map.get_tile(cell_pos.level, cell_pos.x, cell_pos.y)
            if tile is None:
                continue
            self._render_dungeon_layer(tile, position.facing, depth, max_depth)

    def _render_dungeon_layer(
        self,
        tile: TileData,
        facing: Direction,
        depth: int,
        max_depth: int,
    ) -> None:
        """Render one layer of the dungeon view at a given depth."""
        # Calculate perspective scaling
        # Objects at depth 0 (closest) are largest, depth max_depth are smallest
        far = max_depth
        scale = 1.0 / (depth + 1)
        next_scale = 1.0 / (depth + 2) if depth < max_depth - 1 else 0.0

        cx = VIEWPORT_X + VIEWPORT_W // 2
        cy = VIEWPORT_Y + VIEWPORT_H // 2

        half_w = int(VIEWPORT_W * scale / 2)
        half_h = int(VIEWPORT_H * scale / 2)
        next_half_w = int(VIEWPORT_W * next_scale / 2)
        next_half_h = int(VIEWPORT_H * next_scale / 2)

        # Shade walls based on distance
        shade = max(0.3, 1.0 - depth * 0.2)

        def shaded(color: tuple[int, int, int]) -> tuple[int, int, int]:
            return (
                int(color[0] * shade),
                int(color[1] * shade),
                int(color[2] * shade),
            )

        # Determine which walls are visible from this facing
        left_dir = facing.turn_left()
        right_dir = facing.turn_right()

        # Left wall
        left_wall = tile.get_wall(left_dir)
        if left_wall != WallType.NONE:
            color = COLOR_DOOR if left_wall == WallType.DOOR else COLOR_WALL
            if left_wall == WallType.SECRET:
                color = COLOR_SECRET
            x1 = cx - half_w
            x2 = cx - next_half_w if depth < max_depth - 1 else cx
            y1_top = cy - half_h
            y1_bot = cy + half_h
            y2_top = cy - next_half_h
            y2_bot = cy + next_half_h
            points = [(x1, y1_top), (x2, y2_top), (x2, y2_bot), (x1, y1_bot)]
            pygame.draw.polygon(self.internal, shaded(color), points)
            pygame.draw.polygon(self.internal, shaded(COLOR_DARK_GRAY), points, 1)

        # Right wall
        right_wall = tile.get_wall(right_dir)
        if right_wall != WallType.NONE:
            color = COLOR_DOOR if right_wall == WallType.DOOR else COLOR_WALL
            if right_wall == WallType.SECRET:
                color = COLOR_SECRET
            x1 = cx + half_w
            x2 = cx + next_half_w if depth < max_depth - 1 else cx
            y1_top = cy - half_h
            y1_bot = cy + half_h
            y2_top = cy - next_half_h
            y2_bot = cy + next_half_h
            points = [(x1, y1_top), (x2, y2_top), (x2, y2_bot), (x1, y1_bot)]
            pygame.draw.polygon(self.internal, shaded(color), points)
            pygame.draw.polygon(self.internal, shaded(COLOR_DARK_GRAY), points, 1)

        # Front wall (blocks view)
        front_wall = tile.get_wall(facing)
        if front_wall != WallType.NONE:
            color = COLOR_DOOR if front_wall == WallType.DOOR else COLOR_WALL
            if front_wall == WallType.SECRET:
                color = COLOR_SECRET
            x1 = cx - half_w
            y1 = cy - half_h
            w = half_w * 2
            h = half_h * 2
            self.draw_rect(x1, y1, w, h, shaded(color))
            self.draw_rect(x1, y1, w, h, shaded(COLOR_DARK_GRAY), filled=False)
            # Door decoration
            if front_wall == WallType.DOOR:
                door_w = w // 3
                door_h = h * 2 // 3
                door_x = x1 + (w - door_w) // 2
                door_y = y1 + h - door_h
                self.draw_rect(door_x, door_y, door_w, door_h, shaded((80, 60, 30)))
                self.draw_rect(
                    door_x, door_y, door_w, door_h,
                    shaded(COLOR_DARK_GRAY), filled=False,
                )
