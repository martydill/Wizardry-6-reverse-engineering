"""Wizardry 6 dungeon renderer with CORRECT texture orientation.

FINAL CORRECT FORMAT:
- 4-bit grayscale intensity values
- Textures stored as VERTICAL columns (200 pixels tall)
- Need to TRANSPOSE the atlas (swap rows/columns)
"""

import pygame
import sys
from pathlib import Path
from dataclasses import dataclass
from enum import IntEnum

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, Sprite


class Direction(IntEnum):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3


@dataclass
class Player:
    x: int = 1
    y: int = 1
    direction: Direction = Direction.NORTH


def create_grayscale_palette():
    """Create 16-level grayscale palette."""
    palette = []
    for i in range(16):
        gray = int((i / 15.0) * 255)
        palette.append((gray, gray, gray))
    return palette


def transpose_sprite(sprite: Sprite) -> Sprite:
    """Transpose sprite (swap rows and columns)."""
    new_pixels = []
    for x in range(sprite.width):
        for y in range(sprite.height):
            new_pixels.append(sprite.get_pixel(x, y))

    return Sprite(
        width=sprite.height,
        height=sprite.width,
        pixels=new_pixels,
        palette=sprite.palette
    )


class VerticalTextureAtlas:
    """Manages MAZEDATA textures with CORRECT vertical column orientation."""

    def __init__(self, atlas_sprite: Sprite):
        # CRITICAL: Transpose the atlas to get vertical columns
        self.atlas = transpose_sprite(atlas_sprite)
        self.columns = self._extract_columns()
        self.pygame_surfaces = self._create_pygame_surfaces()
        self.colorized_cache = {}

    def _extract_columns(self) -> list[Sprite]:
        """Extract vertical texture columns from atlas.

        Each column is a separate wall texture (200 pixels tall).
        """
        columns = []
        column_width = 32  # Try 32-pixel wide columns

        num_columns = self.atlas.width // column_width

        for col_idx in range(num_columns):
            x_start = col_idx * column_width
            x_end = x_start + column_width

            pixels = []
            for y in range(self.atlas.height):
                for x in range(x_start, min(x_end, self.atlas.width)):
                    pixels.append(self.atlas.get_pixel(x, y))

            column = Sprite(
                width=column_width,
                height=self.atlas.height,
                pixels=pixels,
                palette=self.atlas.palette
            )
            columns.append(column)

        return columns

    def _create_pygame_surfaces(self) -> list[pygame.Surface]:
        """Convert texture columns to pygame surfaces."""
        surfaces = []
        for column in self.columns:
            surf = pygame.Surface((column.width, column.height))
            for y in range(column.height):
                for x in range(column.width):
                    intensity = column.get_pixel(x, y)
                    if 0 <= intensity < len(column.palette):
                        surf.set_at((x, y), column.palette[intensity])
            surfaces.append(surf)
        return surfaces

    def get_surface(self, column_id: int) -> pygame.Surface:
        """Get grayscale surface for a texture column."""
        if 0 <= column_id < len(self.pygame_surfaces):
            return self.pygame_surfaces[column_id]
        return self.pygame_surfaces[0]

    def get_colorized_surface(self, column_id: int, tint_color: tuple[int, int, int]) -> pygame.Surface:
        """Get colorized version of a texture column."""
        cache_key = (column_id, tint_color)

        if cache_key in self.colorized_cache:
            return self.colorized_cache[cache_key]

        grayscale_surf = self.get_surface(column_id)
        width, height = grayscale_surf.get_size()

        colorized = pygame.Surface((width, height))

        for y in range(height):
            for x in range(width):
                gray_color = grayscale_surf.get_at((x, y))
                gray_value = gray_color[0]

                r = int((gray_value / 255.0) * tint_color[0])
                g = int((gray_value / 255.0) * tint_color[1])
                b = int((gray_value / 255.0) * tint_color[2])

                colorized.set_at((x, y), (r, g, b))

        self.colorized_cache[cache_key] = colorized
        return colorized


class FinalDungeonRenderer:
    """Final corrected dungeon renderer with vertical texture columns."""

    def __init__(self, width: int = 800, height: int = 600):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Wizardry 6 - FINAL CORRECT Textures!")

        self.textures = self._load_textures()

        # Test dungeon
        self.dungeon = [
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            [1, 0, 0, 0, 2, 0, 0, 0, 0, 0, 3, 1],
            [1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1],
            [1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1],
            [1, 0, 0, 0, 2, 1, 0, 0, 0, 1, 0, 1],
            [1, 0, 1, 1, 1, 0, 0, 1, 3, 1, 0, 1],
            [1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1],
            [1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1],
            [1, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0, 1],
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        ]

        # Wall type to texture column mapping
        self.wall_texture_map = {
            1: 1,  # Stone wall -> column 1
            2: 2,  # Brick wall -> column 2
            3: 3,  # Blue stone -> column 3
        }

        # Wall colors for colorization
        self.wall_colors = {
            1: (180, 180, 180),  # Stone: Gray
            2: (150, 120, 100),  # Brick: Brown
            3: (120, 140, 160),  # Blue stone: Blue
        }

        self.player = Player(x=1, y=1, direction=Direction.NORTH)
        self.clock = pygame.time.Clock()
        self.show_minimap = True
        self.show_info = True
        self.use_colorization = True

    def _load_textures(self) -> VerticalTextureAtlas:
        """Load MAZEDATA.EGA with correct orientation."""
        gamedata = Path("gamedata")
        path = gamedata / "MAZEDATA.EGA"

        if not path.exists():
            print(f"Error: {path} not found")
            sys.exit(1)

        data = path.read_bytes()

        # Decode as grayscale 320x200
        grayscale_palette = create_grayscale_palette()
        decoder = EGADecoder(palette=grayscale_palette)
        atlas = decoder.decode_planar(
            data[:32000],
            width=320,
            height=200,
            msb_first=True
        )

        # VerticalTextureAtlas will transpose it automatically
        return VerticalTextureAtlas(atlas)

    def get_tile(self, x: int, y: int) -> int:
        """Get tile at position."""
        if 0 <= y < len(self.dungeon) and 0 <= x < len(self.dungeon[0]):
            return self.dungeon[y][x]
        return 1

    def render_frame(self):
        """Render complete frame."""
        # Clear with floor/ceiling
        pygame.draw.rect(self.screen, (20, 20, 30), (0, 0, self.width, self.height // 2))
        pygame.draw.rect(self.screen, (40, 30, 20), (0, self.height // 2, self.width, self.height // 2))

        # Render walls
        distances = [
            (5, 50, 40),
            (4, 80, 80),
            (3, 140, 140),
            (2, 240, 220),
            (1, 400, 360),
        ]

        for distance, wall_width, wall_height in distances:
            self._render_walls_at_distance(distance, wall_width, wall_height)

        if self.show_minimap:
            self._draw_minimap()

        if self.show_info:
            self._draw_hud()

        pygame.display.flip()

    def _render_walls_at_distance(self, distance: int, wall_width: int, wall_height: int):
        """Render walls at specific distance."""
        dx, dy = self._get_direction_delta(self.player.direction)
        check_x = self.player.x + dx * distance
        check_y = self.player.y + dy * distance

        center_x = self.width // 2
        center_y = self.height // 2

        # Front wall
        tile = self.get_tile(check_x, check_y)
        if tile > 0:
            texture_col = self.wall_texture_map.get(tile, 1)
            wall_color = self.wall_colors.get(tile, (180, 180, 180))

            self._draw_textured_wall(
                center_x - wall_width // 2,
                center_y - wall_height // 2,
                wall_width,
                wall_height,
                texture_col,
                wall_color,
                distance
            )

        # Side walls
        ldx, ldy = self._get_perpendicular_left(self.player.direction)
        rdx, rdy = self._get_perpendicular_right(self.player.direction)

        left_x, left_y = check_x + ldx, check_y + ldy
        right_x, right_y = check_x + rdx, check_y + rdy

        # Left wall
        left_tile = self.get_tile(left_x, left_y)
        if left_tile > 0:
            side_width = wall_width // 4
            texture_col = self.wall_texture_map.get(left_tile, 1)
            wall_color = self.wall_colors.get(left_tile, (180, 180, 180))

            self._draw_textured_wall(
                center_x - wall_width // 2 - side_width,
                center_y - wall_height // 2,
                side_width,
                wall_height,
                texture_col,
                wall_color,
                distance,
                darken=0.7
            )

        # Right wall
        right_tile = self.get_tile(right_x, right_y)
        if right_tile > 0:
            side_width = wall_width // 4
            texture_col = self.wall_texture_map.get(right_tile, 1)
            wall_color = self.wall_colors.get(right_tile, (180, 180, 180))

            self._draw_textured_wall(
                center_x + wall_width // 2,
                center_y - wall_height // 2,
                side_width,
                wall_height,
                texture_col,
                wall_color,
                distance,
                darken=0.7
            )

    def _draw_textured_wall(self, x: int, y: int, width: int, height: int,
                           texture_col: int, wall_color: tuple, distance: int, darken: float = 1.0):
        """Draw wall with texture."""
        if self.use_colorization:
            texture_surf = self.textures.get_colorized_surface(texture_col, wall_color)
        else:
            texture_surf = self.textures.get_surface(texture_col)

        scaled_texture = pygame.transform.scale(texture_surf, (width, height))

        darkness = max(0.3, 1.0 - (distance - 1) * 0.15) * darken

        if darkness < 1.0:
            dark_overlay = pygame.Surface((width, height))
            dark_overlay.fill((0, 0, 0))
            dark_overlay.set_alpha(int(255 * (1.0 - darkness)))
            scaled_texture.blit(dark_overlay, (0, 0))

        self.screen.blit(scaled_texture, (x, y))

    def _get_direction_delta(self, direction: Direction) -> tuple[int, int]:
        deltas = {Direction.NORTH: (0, -1), Direction.SOUTH: (0, 1),
                  Direction.EAST: (1, 0), Direction.WEST: (-1, 0)}
        return deltas[direction]

    def _get_perpendicular_left(self, direction: Direction) -> tuple[int, int]:
        return self._get_direction_delta(Direction((direction - 1) % 4))

    def _get_perpendicular_right(self, direction: Direction) -> tuple[int, int]:
        return self._get_direction_delta(Direction((direction + 1) % 4))

    def _draw_minimap(self):
        """Draw minimap."""
        map_size, map_x, map_y = 150, self.width - 170, 20

        minimap_surf = pygame.Surface((map_size, map_size))
        minimap_surf.set_alpha(200)
        minimap_surf.fill((0, 0, 0))
        self.screen.blit(minimap_surf, (map_x, map_y))
        pygame.draw.rect(self.screen, (100, 100, 100), (map_x, map_y, map_size, map_size), 2)

        cell_w = map_size // len(self.dungeon[0])
        cell_h = map_size // len(self.dungeon)

        for y, row in enumerate(self.dungeon):
            for x, tile in enumerate(row):
                px, py = map_x + x * cell_w, map_y + y * cell_h

                if tile > 0:
                    color = tuple(c // 2 for c in self.wall_colors.get(tile, (180, 180, 180)))
                    pygame.draw.rect(self.screen, color, (px, py, cell_w, cell_h))
                else:
                    pygame.draw.rect(self.screen, (40, 40, 40), (px, py, cell_w, cell_h))

                pygame.draw.rect(self.screen, (60, 60, 60), (px, py, cell_w, cell_h), 1)

        px = map_x + self.player.x * cell_w + cell_w // 2
        py = map_y + self.player.y * cell_h + cell_h // 2
        pygame.draw.circle(self.screen, (255, 255, 0), (px, py), 3)

        dx, dy = self._get_direction_delta(self.player.direction)
        pygame.draw.line(self.screen, (255, 255, 0), (px, py),
                        (px + dx * 8, py + dy * 8), 2)

    def _draw_hud(self):
        """Draw HUD."""
        font = pygame.font.Font(None, 24)
        small_font = pygame.font.Font(None, 18)

        dir_names = ["North", "East", "South", "West"]
        pos_text = f"Pos: ({self.player.x},{self.player.y}) | Dir: {dir_names[self.player.direction]}"
        self.screen.blit(font.render(pos_text, True, (255, 255, 255)), (10, 10))

        colorization = "ON" if self.use_colorization else "OFF"
        info_lines = [
            "FINAL CORRECT FORMAT: Vertical texture columns!",
            f"Colorization: {colorization} | Textures: {len(self.textures.columns)} columns",
            "",
            "Controls: Arrows=Move | Q/E=Turn | C=Color | M=Map | I=Info | ESC=Quit"
        ]

        y_offset = self.height - 90
        for line in info_lines:
            self.screen.blit(small_font.render(line, True, (200, 200, 200)), (10, y_offset))
            y_offset += 18

    def handle_input(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_UP:
                    dx, dy = self._get_direction_delta(self.player.direction)
                    new_x, new_y = self.player.x + dx, self.player.y + dy
                    if self.get_tile(new_x, new_y) == 0:
                        self.player.x, self.player.y = new_x, new_y
                elif event.key == pygame.K_DOWN:
                    dx, dy = self._get_direction_delta(self.player.direction)
                    new_x, new_y = self.player.x - dx, self.player.y - dy
                    if self.get_tile(new_x, new_y) == 0:
                        self.player.x, self.player.y = new_x, new_y
                elif event.key in (pygame.K_LEFT, pygame.K_q):
                    self.player.direction = Direction((self.player.direction - 1) % 4)
                elif event.key in (pygame.K_RIGHT, pygame.K_e):
                    self.player.direction = Direction((self.player.direction + 1) % 4)
                elif event.key == pygame.K_m:
                    self.show_minimap = not self.show_minimap
                elif event.key == pygame.K_i:
                    self.show_info = not self.show_info
                elif event.key == pygame.K_c:
                    self.use_colorization = not self.use_colorization
                    self.textures.colorized_cache.clear()

        return True

    def run(self):
        print("Wizardry 6 Final Dungeon Renderer")
        print("=" * 70)
        print("FINAL CORRECT FORMAT:")
        print("  - 4-bit grayscale intensity values")
        print("  - VERTICAL texture columns (transposed)")
        print("  - Runtime colorization")
        print()
        print(f"Loaded {len(self.textures.columns)} texture columns")
        print()
        print("Controls:")
        print("  Arrow Keys: Move")
        print("  Q/E: Turn left/right")
        print("  C: Toggle colorization")
        print("  M: Toggle minimap")
        print("  I: Toggle info")
        print("  ESC: Quit")
        print("=" * 70)

        running = True
        while running:
            running = self.handle_input()
            self.render_frame()
            self.clock.tick(30)

        pygame.quit()


def main():
    renderer = FinalDungeonRenderer()
    renderer.run()


if __name__ == "__main__":
    main()
