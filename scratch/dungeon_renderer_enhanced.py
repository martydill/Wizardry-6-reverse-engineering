"""Enhanced first-person dungeon renderer with minimap and better graphics.

Features:
- Textured walls using MAZEDATA.EGA bands
- Minimap showing dungeon layout
- Multiple depth levels (5 distances)
- Floor and ceiling rendering
- Smooth wall texturing
"""

import pygame
import sys
from pathlib import Path
from dataclasses import dataclass
from enum import IntEnum

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, Sprite


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


class TextureAtlas:
    """Manages MAZEDATA.EGA texture bands with caching."""

    def __init__(self, atlas_sprite: Sprite):
        self.atlas = atlas_sprite
        self.bands = self._extract_bands()
        self.pygame_surfaces = self._create_pygame_surfaces()

    def _extract_bands(self) -> list[Sprite]:
        """Extract texture bands from atlas."""
        bands = []
        band_configs = [
            (0, 32),    # Band 0: Stone
            (32, 64),   # Band 1: Red brick
            (64, 96),   # Band 2: Blue tiles
            (96, 128),  # Band 3: Dark
            (128, 160), # Band 4: Gray stone
            (160, 200), # Band 5: Purple
        ]

        for y_start, y_end in band_configs:
            pixels = []
            for y in range(y_start, y_end):
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
        """Convert texture bands to pygame surfaces for faster rendering."""
        surfaces = []
        for band in self.bands:
            surf = pygame.Surface((band.width, band.height))
            for y in range(band.height):
                for x in range(band.width):
                    color_idx = band.get_pixel(x, y)
                    if 0 <= color_idx < len(band.palette):
                        surf.set_at((x, y), band.palette[color_idx])
            surfaces.append(surf)
        return surfaces

    def get_surface(self, band_id: int) -> pygame.Surface:
        """Get pygame surface for a texture band."""
        if 0 <= band_id < len(self.pygame_surfaces):
            return self.pygame_surfaces[band_id]
        return self.pygame_surfaces[0]


class EnhancedDungeonRenderer:
    """Enhanced 3D dungeon renderer."""

    def __init__(self, width: int = 800, height: int = 600):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Wizardry 6 Enhanced Dungeon Renderer")

        self.textures = self._load_textures()

        # Test dungeon with different wall types
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

        self.player = Player(x=1, y=1, direction=Direction.NORTH)
        self.clock = pygame.time.Clock()
        self.show_minimap = True

    def _load_textures(self) -> TextureAtlas:
        """Load MAZEDATA.EGA textures."""
        gamedata = Path("gamedata")
        path = gamedata / "MAZEDATA.EGA"

        if not path.exists():
            print(f"Error: {path} not found")
            sys.exit(1)

        data = path.read_bytes()
        decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
        atlas = decoder.decode_planar(data[:32000], width=320, height=200, msb_first=True)

        return TextureAtlas(atlas)

    def get_tile(self, x: int, y: int) -> int:
        """Get tile at position."""
        if 0 <= y < len(self.dungeon) and 0 <= x < len(self.dungeon[0]):
            return self.dungeon[y][x]
        return 1

    def render_frame(self):
        """Render complete frame."""
        # Clear with floor/ceiling colors
        self.screen.fill((40, 40, 40))

        # Render ceiling (top half darker)
        pygame.draw.rect(self.screen, (20, 20, 30), (0, 0, self.width, self.height // 2))

        # Render floor (bottom half)
        pygame.draw.rect(self.screen, (50, 40, 30), (0, self.height // 2, self.width, self.height // 2))

        # Render walls at multiple distances (back to front for proper occlusion)
        distances = [
            (5, 50, 40),    # Very far
            (4, 80, 80),    # Far
            (3, 140, 140),  # Medium-far
            (2, 240, 220),  # Medium
            (1, 400, 360),  # Near
        ]

        for distance, wall_width, wall_height in distances:
            self._render_walls_at_distance(distance, wall_width, wall_height)

        # Draw minimap
        if self.show_minimap:
            self._draw_minimap()

        # Draw HUD
        self._draw_hud()

        pygame.display.flip()

    def _render_walls_at_distance(self, distance: int, wall_width: int, wall_height: int):
        """Render walls at specific distance."""
        # Calculate viewing position
        dx, dy = self._get_direction_delta(self.player.direction)
        check_x = self.player.x + dx * distance
        check_y = self.player.y + dy * distance

        center_x = self.width // 2
        center_y = self.height // 2

        # Front wall
        tile = self.get_tile(check_x, check_y)
        if tile > 0:
            self._draw_textured_wall(
                center_x - wall_width // 2,
                center_y - wall_height // 2,
                wall_width,
                wall_height,
                tile - 1,
                distance
            )

        # Left and right walls
        ldx, ldy = self._get_perpendicular_left(self.player.direction)
        rdx, rdy = self._get_perpendicular_right(self.player.direction)

        left_x, left_y = check_x + ldx, check_y + ldy
        right_x, right_y = check_x + rdx, check_y + rdy

        # Left wall (narrower for perspective)
        left_tile = self.get_tile(left_x, left_y)
        if left_tile > 0:
            side_width = wall_width // 4
            self._draw_textured_wall(
                center_x - wall_width // 2 - side_width,
                center_y - wall_height // 2,
                side_width,
                wall_height,
                left_tile - 1,
                distance,
                darken=0.7
            )

        # Right wall
        right_tile = self.get_tile(right_x, right_y)
        if right_tile > 0:
            side_width = wall_width // 4
            self._draw_textured_wall(
                center_x + wall_width // 2,
                center_y - wall_height // 2,
                side_width,
                wall_height,
                right_tile - 1,
                distance,
                darken=0.7
            )

    def _draw_textured_wall(self, x: int, y: int, width: int, height: int,
                           texture_id: int, distance: int, darken: float = 1.0):
        """Draw a wall with texture."""
        texture_surf = self.textures.get_surface(texture_id % len(self.textures.pygame_surfaces))

        # Scale texture to wall size
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
        """Get dx, dy for a direction."""
        if direction == Direction.NORTH:
            return (0, -1)
        elif direction == Direction.SOUTH:
            return (0, 1)
        elif direction == Direction.EAST:
            return (1, 0)
        else:  # WEST
            return (-1, 0)

    def _get_perpendicular_left(self, direction: Direction) -> tuple[int, int]:
        """Get perpendicular left direction."""
        left_dir = Direction((direction - 1) % 4)
        return self._get_direction_delta(left_dir)

    def _get_perpendicular_right(self, direction: Direction) -> tuple[int, int]:
        """Get perpendicular right direction."""
        right_dir = Direction((direction + 1) % 4)
        return self._get_direction_delta(right_dir)

    def _draw_minimap(self):
        """Draw minimap overlay."""
        map_size = 150
        map_x = self.width - map_size - 20
        map_y = 20

        # Background
        pygame.draw.rect(self.screen, (0, 0, 0, 128), (map_x, map_y, map_size, map_size))
        pygame.draw.rect(self.screen, (100, 100, 100), (map_x, map_y, map_size, map_size), 2)

        # Calculate cell size
        cell_w = map_size // len(self.dungeon[0])
        cell_h = map_size // len(self.dungeon)

        # Draw dungeon
        for y, row in enumerate(self.dungeon):
            for x, tile in enumerate(row):
                px = map_x + x * cell_w
                py = map_y + y * cell_h

                if tile > 0:
                    # Wall colors based on type
                    colors = [(100, 100, 100), (150, 80, 80), (80, 80, 150), (120, 100, 120)]
                    color = colors[min(tile - 1, len(colors) - 1)]
                    pygame.draw.rect(self.screen, color, (px, py, cell_w, cell_h))
                else:
                    # Empty space
                    pygame.draw.rect(self.screen, (40, 40, 40), (px, py, cell_w, cell_h))

                # Grid lines
                pygame.draw.rect(self.screen, (60, 60, 60), (px, py, cell_w, cell_h), 1)

        # Draw player
        px = map_x + self.player.x * cell_w + cell_w // 2
        py = map_y + self.player.y * cell_h + cell_h // 2
        pygame.draw.circle(self.screen, (255, 255, 0), (px, py), 3)

        # Draw direction indicator
        dir_len = 8
        dx, dy = self._get_direction_delta(self.player.direction)
        pygame.draw.line(self.screen, (255, 255, 0),
                        (px, py),
                        (px + dx * dir_len, py + dy * dir_len), 2)

    def _draw_hud(self):
        """Draw HUD."""
        font = pygame.font.Font(None, 24)
        small_font = pygame.font.Font(None, 18)

        # Position
        dir_names = ["North", "East", "South", "West"]
        pos_text = f"Pos: ({self.player.x},{self.player.y}) | Dir: {dir_names[self.player.direction]}"
        text_surf = font.render(pos_text, True, (255, 255, 255))
        self.screen.blit(text_surf, (10, 10))

        # Controls
        controls = [
            "Controls: Arrow Keys=Move | Q/E=Turn | M=Toggle Map | ESC=Quit",
            "Wall Colors: Gray=Stone | Red=Brick | Blue=Tiles | Purple=Decorative"
        ]

        for i, text in enumerate(controls):
            surf = small_font.render(text, True, (200, 200, 200))
            self.screen.blit(surf, (10, self.height - 50 + i * 20))

    def move_forward(self):
        dx, dy = self._get_direction_delta(self.player.direction)
        new_x = self.player.x + dx
        new_y = self.player.y + dy
        if self.get_tile(new_x, new_y) == 0:
            self.player.x, self.player.y = new_x, new_y

    def move_backward(self):
        dx, dy = self._get_direction_delta(self.player.direction)
        new_x = self.player.x - dx
        new_y = self.player.y - dy
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

        return True

    def run(self):
        print("Enhanced Wizardry 6 Style Dungeon Renderer")
        print("=" * 50)
        print("Controls:")
        print("  Arrow Keys / Q,E: Move and turn")
        print("  M: Toggle minimap")
        print("  ESC: Quit")
        print("\nExplore the dungeon!")
        print("Different colored walls use different MAZEDATA texture bands.")

        running = True
        while running:
            running = self.handle_input()
            self.render_frame()
            self.clock.tick(30)

        pygame.quit()


def main():
    renderer = EnhancedDungeonRenderer()
    renderer.run()


if __name__ == "__main__":
    main()
