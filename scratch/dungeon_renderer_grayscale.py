"""Wizardry 6 dungeon renderer using GRAYSCALE textures.

CORRECT FORMAT: 4-bit values are grayscale intensities (0-15),
not color palette indices. Game colorizes at runtime.
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


def create_grayscale_palette() -> list[tuple[int, int, int]]:
    """Create 16-level grayscale palette."""
    palette = []
    for i in range(16):
        gray = int((i / 15.0) * 255)
        palette.append((gray, gray, gray))
    return palette


class GrayscaleTextureAtlas:
    """Manages grayscale MAZEDATA.EGA textures."""

    def __init__(self, atlas_sprite: Sprite):
        self.atlas = atlas_sprite
        self.bands = self._extract_bands()
        self.pygame_surfaces = self._create_pygame_surfaces()

        # Pre-create colorized versions for different wall types
        self.colorized_cache = {}

    def _extract_bands(self) -> list[Sprite]:
        """Extract texture bands from atlas."""
        bands = []
        band_configs = [
            (0, 32),      # Band 0
            (32, 64),     # Band 1
            (64, 96),     # Band 2
            (96, 128),    # Band 3
            (128, 160),   # Band 4 - clearest patterns
            (160, 200),   # Band 5
        ]

        for y_start, y_end in band_configs:
            pixels = []
            for y in range(y_start, min(y_end, self.atlas.height)):
                for x in range(self.atlas.width):
                    pixels.append(self.atlas.get_pixel(x, y))

            band = Sprite(
                width=self.atlas.width,
                height=y_end - y_start,
                pixels=pixels,
                palette=self.atlas.palette
            )
            bands.append(band)

        return bands

    def _create_pygame_surfaces(self) -> list[pygame.Surface]:
        """Convert grayscale texture bands to pygame surfaces."""
        surfaces = []
        for band in self.bands:
            surf = pygame.Surface((band.width, band.height))
            for y in range(band.height):
                for x in range(band.width):
                    intensity = band.get_pixel(x, y)
                    if 0 <= intensity < len(band.palette):
                        surf.set_at((x, y), band.palette[intensity])
            surfaces.append(surf)
        return surfaces

    def get_surface(self, band_id: int) -> pygame.Surface:
        """Get grayscale surface for a texture band."""
        if 0 <= band_id < len(self.pygame_surfaces):
            return self.pygame_surfaces[band_id]
        return self.pygame_surfaces[0]

    def get_colorized_surface(self, band_id: int, tint_color: tuple[int, int, int]) -> pygame.Surface:
        """Get colorized version of a texture band.

        Args:
            band_id: Which texture band to use
            tint_color: RGB color to tint the grayscale texture with
        """
        cache_key = (band_id, tint_color)

        if cache_key in self.colorized_cache:
            return self.colorized_cache[cache_key]

        # Get grayscale surface
        grayscale_surf = self.get_surface(band_id)
        width, height = grayscale_surf.get_size()

        # Create colorized version
        colorized = pygame.Surface((width, height))

        for y in range(height):
            for x in range(width):
                # Get grayscale value (0-255)
                gray_color = grayscale_surf.get_at((x, y))
                gray_value = gray_color[0]  # R=G=B in grayscale

                # Apply tint color based on grayscale intensity
                # intensity = gray_value / 255.0
                r = int((gray_value / 255.0) * tint_color[0])
                g = int((gray_value / 255.0) * tint_color[1])
                b = int((gray_value / 255.0) * tint_color[2])

                colorized.set_at((x, y), (r, g, b))

        self.colorized_cache[cache_key] = colorized
        return colorized


class GrayscaleDungeonRenderer:
    """Dungeon renderer using grayscale textures with runtime colorization."""

    def __init__(self, width: int = 800, height: int = 600):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Wizardry 6 - Grayscale Textures (CORRECT!)")

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

        # Wall type colors (for colorizing grayscale textures)
        self.wall_colors = [
            (180, 180, 180),  # Type 0: Light gray stone
            (150, 120, 100),  # Type 1: Brown brick
            (120, 140, 160),  # Type 2: Blue stone
            (140, 100, 140),  # Type 3: Purple stone
        ]

        self.player = Player(x=1, y=1, direction=Direction.NORTH)
        self.clock = pygame.time.Clock()
        self.show_minimap = True
        self.show_info = True
        self.use_colorization = True

    def _load_textures(self) -> GrayscaleTextureAtlas:
        """Load MAZEDATA.EGA as grayscale textures."""
        gamedata = Path("gamedata")
        path = gamedata / "MAZEDATA.EGA"

        if not path.exists():
            print(f"Error: {path} not found")
            sys.exit(1)

        data = path.read_bytes()

        # CORRECT: Decode as grayscale (4-bit intensity values)
        grayscale_palette = create_grayscale_palette()
        decoder = EGADecoder(palette=grayscale_palette)
        atlas = decoder.decode_planar(
            data[:32000],
            width=320,
            height=200,
            msb_first=True
        )

        return GrayscaleTextureAtlas(atlas)

    def get_tile(self, x: int, y: int) -> int:
        """Get tile at position."""
        if 0 <= y < len(self.dungeon) and 0 <= x < len(self.dungeon[0]):
            return self.dungeon[y][x]
        return 1

    def render_frame(self):
        """Render complete frame."""
        # Clear with floor/ceiling colors
        pygame.draw.rect(self.screen, (20, 20, 30), (0, 0, self.width, self.height // 2))
        pygame.draw.rect(self.screen, (40, 30, 20), (0, self.height // 2, self.width, self.height // 2))

        # Render walls at multiple distances
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
            # Use band 3 or 4 for best wall patterns
            texture_band = 3 if tile == 1 else 4

            self._draw_textured_wall(
                center_x - wall_width // 2,
                center_y - wall_height // 2,
                wall_width,
                wall_height,
                texture_band,
                tile - 1,  # Wall type for colorization
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
            texture_band = 3 if left_tile == 1 else 4

            self._draw_textured_wall(
                center_x - wall_width // 2 - side_width,
                center_y - wall_height // 2,
                side_width,
                wall_height,
                texture_band,
                left_tile - 1,
                distance,
                darken=0.7
            )

        # Right wall
        right_tile = self.get_tile(right_x, right_y)
        if right_tile > 0:
            side_width = wall_width // 4
            texture_band = 3 if right_tile == 1 else 4

            self._draw_textured_wall(
                center_x + wall_width // 2,
                center_y - wall_height // 2,
                side_width,
                wall_height,
                texture_band,
                right_tile - 1,
                distance,
                darken=0.7
            )

    def _draw_textured_wall(self, x: int, y: int, width: int, height: int,
                           texture_band: int, wall_type: int, distance: int, darken: float = 1.0):
        """Draw wall with grayscale texture (optionally colorized)."""

        # Get texture (grayscale or colorized)
        if self.use_colorization:
            wall_color = self.wall_colors[wall_type % len(self.wall_colors)]
            texture_surf = self.textures.get_colorized_surface(texture_band, wall_color)
        else:
            texture_surf = self.textures.get_surface(texture_band)

        # Scale to wall size (nearest neighbor to preserve pixels)
        scaled_texture = pygame.transform.scale(texture_surf, (width, height))

        # Apply distance darkening
        darkness = max(0.3, 1.0 - (distance - 1) * 0.15)
        darkness *= darken

        if darkness < 1.0:
            dark_overlay = pygame.Surface((width, height))
            dark_overlay.fill((0, 0, 0))
            dark_overlay.set_alpha(int(255 * (1.0 - darkness)))
            scaled_texture.blit(dark_overlay, (0, 0))

        self.screen.blit(scaled_texture, (x, y))

    def _get_direction_delta(self, direction: Direction) -> tuple[int, int]:
        deltas = {
            Direction.NORTH: (0, -1),
            Direction.SOUTH: (0, 1),
            Direction.EAST: (1, 0),
            Direction.WEST: (-1, 0)
        }
        return deltas[direction]

    def _get_perpendicular_left(self, direction: Direction) -> tuple[int, int]:
        left_dir = Direction((direction - 1) % 4)
        return self._get_direction_delta(left_dir)

    def _get_perpendicular_right(self, direction: Direction) -> tuple[int, int]:
        right_dir = Direction((direction + 1) % 4)
        return self._get_direction_delta(right_dir)

    def _draw_minimap(self):
        """Draw minimap overlay."""
        map_size = 150
        map_x = self.width - map_size - 20
        map_y = 20

        minimap_surf = pygame.Surface((map_size, map_size))
        minimap_surf.set_alpha(200)
        minimap_surf.fill((0, 0, 0))
        self.screen.blit(minimap_surf, (map_x, map_y))

        pygame.draw.rect(self.screen, (100, 100, 100), (map_x, map_y, map_size, map_size), 2)

        cell_w = map_size // len(self.dungeon[0])
        cell_h = map_size // len(self.dungeon)

        for y, row in enumerate(self.dungeon):
            for x, tile in enumerate(row):
                px = map_x + x * cell_w
                py = map_y + y * cell_h

                if tile > 0:
                    color = self.wall_colors[(tile - 1) % len(self.wall_colors)]
                    color = tuple(c // 2 for c in color)  # Darken for minimap
                    pygame.draw.rect(self.screen, color, (px, py, cell_w, cell_h))
                else:
                    pygame.draw.rect(self.screen, (40, 40, 40), (px, py, cell_w, cell_h))

                pygame.draw.rect(self.screen, (60, 60, 60), (px, py, cell_w, cell_h), 1)

        px = map_x + self.player.x * cell_w + cell_w // 2
        py = map_y + self.player.y * cell_h + cell_h // 2
        pygame.draw.circle(self.screen, (255, 255, 0), (px, py), 3)

        dir_len = 8
        dx, dy = self._get_direction_delta(self.player.direction)
        pygame.draw.line(self.screen, (255, 255, 0), (px, py),
                        (px + dx * dir_len, py + dy * dir_len), 2)

    def _draw_hud(self):
        """Draw HUD."""
        font = pygame.font.Font(None, 24)
        small_font = pygame.font.Font(None, 18)

        dir_names = ["North", "East", "South", "West"]
        pos_text = f"Pos: ({self.player.x},{self.player.y}) | Dir: {dir_names[self.player.direction]}"
        text_surf = font.render(pos_text, True, (255, 255, 255))
        self.screen.blit(text_surf, (10, 10))

        colorization_status = "ON" if self.use_colorization else "OFF (grayscale)"

        info_lines = [
            "CORRECT FORMAT: 4-bit Grayscale Textures!",
            f"Colorization: {colorization_status}",
            "",
            "Controls: Arrows=Move | Q/E=Turn | C=Toggle Color | M=Map | I=Info | ESC=Quit"
        ]

        y_offset = self.height - 90
        for line in info_lines:
            surf = small_font.render(line, True, (200, 200, 200))
            self.screen.blit(surf, (10, y_offset))
            y_offset += 18

    def move_forward(self):
        dx, dy = self._get_direction_delta(self.player.direction)
        new_x, new_y = self.player.x + dx, self.player.y + dy
        if self.get_tile(new_x, new_y) == 0:
            self.player.x, self.player.y = new_x, new_y

    def move_backward(self):
        dx, dy = self._get_direction_delta(self.player.direction)
        new_x, new_y = self.player.x - dx, self.player.y - dy
        if self.get_tile(new_x, new_y) == 0:
            self.player.x, self.player.y = new_x, new_y

    def turn_left(self):
        self.player.direction = Direction((self.player.direction - 1) % 4)

    def turn_right(self):
        self.player.direction = Direction((self.player.direction + 1) % 4)

    def handle_input(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_UP:
                    self.move_forward()
                elif event.key == pygame.K_DOWN:
                    self.move_backward()
                elif event.key in (pygame.K_LEFT, pygame.K_q):
                    self.turn_left()
                elif event.key in (pygame.K_RIGHT, pygame.K_e):
                    self.turn_right()
                elif event.key == pygame.K_m:
                    self.show_minimap = not self.show_minimap
                elif event.key == pygame.K_i:
                    self.show_info = not self.show_info
                elif event.key == pygame.K_c:
                    self.use_colorization = not self.use_colorization
                    self.textures.colorized_cache.clear()  # Clear cache

        return True

    def run(self):
        print("Wizardry 6 Grayscale Dungeon Renderer")
        print("=" * 70)
        print("CORRECT FORMAT: 4-bit values = grayscale intensity (0-15)")
        print("Textures are grayscale patterns, colorized at runtime")
        print()
        print("Controls:")
        print("  Arrow Keys: Move")
        print("  Q/E: Turn")
        print("  C: Toggle colorization (ON/OFF)")
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
    renderer = GrayscaleDungeonRenderer()
    renderer.run()


if __name__ == "__main__":
    main()
