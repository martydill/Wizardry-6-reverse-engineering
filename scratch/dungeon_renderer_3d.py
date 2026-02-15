"""First-person 3D dungeon renderer using MAZEDATA.EGA textures.

Classic Wizardry 6-style ray-casting renderer that displays walls
in perspective using the horizontal texture bands.
"""

import pygame
import sys
from pathlib import Path
from dataclasses import dataclass
from enum import IntEnum

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, Sprite


class Direction(IntEnum):
    """Cardinal directions."""
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3


@dataclass
class Player:
    """Player position and orientation."""
    x: int = 1
    y: int = 1
    direction: Direction = Direction.NORTH


class TextureAtlas:
    """Manages MAZEDATA.EGA texture bands."""

    def __init__(self, atlas_sprite: Sprite):
        self.atlas = atlas_sprite
        self.bands = self._extract_bands()

    def _extract_bands(self) -> list[Sprite]:
        """Extract the 6 main texture bands."""
        bands = []
        band_height = 32

        for band_idx in range(6):
            y_start = band_idx * band_height
            y_end = min(y_start + band_height, self.atlas.height)

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

    def get_band(self, band_id: int) -> Sprite:
        """Get a specific texture band."""
        if 0 <= band_id < len(self.bands):
            return self.bands[band_id]
        return self.bands[0]


class DungeonRenderer:
    """3D first-person dungeon renderer."""

    def __init__(self, width: int = 640, height: int = 480):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Wizardry 6 Style Dungeon Renderer")

        # Load MAZEDATA textures
        self.textures = self._load_textures()

        # Simple test dungeon (1 = wall, 0 = empty)
        self.dungeon = [
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            [1, 0, 0, 0, 2, 0, 0, 0, 0, 1],
            [1, 0, 1, 0, 1, 1, 0, 1, 0, 1],
            [1, 0, 1, 0, 0, 0, 0, 1, 0, 1],
            [1, 0, 0, 0, 1, 1, 0, 0, 0, 1],
            [1, 0, 1, 1, 1, 0, 0, 1, 3, 1],
            [1, 0, 0, 0, 0, 0, 1, 1, 0, 1],
            [1, 0, 1, 1, 1, 0, 0, 0, 0, 1],
            [1, 0, 0, 0, 0, 0, 0, 1, 0, 1],
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        ]

        self.player = Player(x=1, y=1, direction=Direction.NORTH)
        self.clock = pygame.time.Clock()

    def _load_textures(self) -> TextureAtlas:
        """Load MAZEDATA.EGA texture atlas."""
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
        """Get dungeon tile at position."""
        if 0 <= y < len(self.dungeon) and 0 <= x < len(self.dungeon[0]):
            return self.dungeon[y][x]
        return 1  # Wall outside bounds

    def render_frame(self):
        """Render one frame of the 3D view."""
        self.screen.fill((0, 0, 0))

        # Render walls at different distances
        # Distance 3 (far)
        self._render_walls_at_distance(3, 120, 80)

        # Distance 2 (medium)
        self._render_walls_at_distance(2, 200, 160)

        # Distance 1 (near)
        self._render_walls_at_distance(1, 320, 280)

        # Draw HUD
        self._draw_hud()

        pygame.display.flip()

    def _render_walls_at_distance(self, distance: int, wall_width: int, wall_height: int):
        """Render walls at a specific distance from player."""
        # Calculate position to check based on distance
        dx, dy = 0, 0
        if self.player.direction == Direction.NORTH:
            dy = -distance
        elif self.player.direction == Direction.SOUTH:
            dy = distance
        elif self.player.direction == Direction.EAST:
            dx = distance
        elif self.player.direction == Direction.WEST:
            dx = -distance

        check_x = self.player.x + dx
        check_y = self.player.y + dy

        # Center position
        center_x = self.width // 2
        center_y = self.height // 2

        # Check front wall
        tile = self.get_tile(check_x, check_y)
        if tile > 0:
            # Front wall - centered
            self._draw_wall(
                center_x - wall_width // 2,
                center_y - wall_height // 2,
                wall_width,
                wall_height,
                tile - 1  # Use tile value as texture band ID
            )

        # Check left and right walls at this distance
        if self.player.direction == Direction.NORTH:
            left_x, left_y = check_x - 1, check_y
            right_x, right_y = check_x + 1, check_y
        elif self.player.direction == Direction.SOUTH:
            left_x, left_y = check_x + 1, check_y
            right_x, right_y = check_x - 1, check_y
        elif self.player.direction == Direction.EAST:
            left_x, left_y = check_x, check_y - 1
            right_x, right_y = check_x, check_y + 1
        else:  # WEST
            left_x, left_y = check_x, check_y + 1
            right_x, right_y = check_x, check_y - 1

        # Left wall
        left_tile = self.get_tile(left_x, left_y)
        if left_tile > 0:
            offset = wall_width // 3
            self._draw_wall(
                center_x - wall_width // 2 - offset,
                center_y - wall_height // 2,
                offset,
                wall_height,
                left_tile - 1
            )

        # Right wall
        right_tile = self.get_tile(right_x, right_y)
        if right_tile > 0:
            offset = wall_width // 3
            self._draw_wall(
                center_x + wall_width // 2,
                center_y - wall_height // 2,
                offset,
                wall_height,
                right_tile - 1
            )

    def _draw_wall(self, x: int, y: int, width: int, height: int, texture_id: int):
        """Draw a wall segment using a texture band."""
        # Get texture band
        texture = self.textures.get_band(texture_id % len(self.textures.bands))

        # Sample and scale the texture
        # For simplicity, we'll sample the middle portion and scale it
        texture_width = min(width, texture.width)
        texture_x_offset = (texture.width - texture_width) // 2

        # Create scaled surface
        wall_surface = pygame.Surface((width, height))

        # Draw texture scaled to wall dimensions
        for px in range(width):
            # Map pixel X to texture X (with tiling)
            tex_x = (texture_x_offset + (px * texture_width // width)) % texture.width

            for py in range(height):
                # Map pixel Y to texture Y
                tex_y = (py * texture.height // height) % texture.height

                # Get pixel color from texture
                color_idx = texture.get_pixel(tex_x, tex_y)
                if 0 <= color_idx < len(texture.palette):
                    color = texture.palette[color_idx]
                    wall_surface.set_at((px, py), color)

        # Draw to screen
        self.screen.blit(wall_surface, (x, y))

    def _draw_hud(self):
        """Draw heads-up display."""
        font = pygame.font.Font(None, 24)

        # Position and direction
        dir_names = ["North", "East", "South", "West"]
        pos_text = f"Position: ({self.player.x}, {self.player.y})  Facing: {dir_names[self.player.direction]}"
        text_surface = font.render(pos_text, True, (255, 255, 255))
        self.screen.blit(text_surface, (10, 10))

        # Controls
        controls = "Arrow Keys: Move | Q/E: Turn | ESC: Quit"
        control_surface = font.render(controls, True, (200, 200, 200))
        self.screen.blit(control_surface, (10, self.height - 30))

    def move_forward(self):
        """Move player forward."""
        dx, dy = 0, 0
        if self.player.direction == Direction.NORTH:
            dy = -1
        elif self.player.direction == Direction.SOUTH:
            dy = 1
        elif self.player.direction == Direction.EAST:
            dx = 1
        elif self.player.direction == Direction.WEST:
            dx = -1

        new_x = self.player.x + dx
        new_y = self.player.y + dy

        # Check if we can move there
        if self.get_tile(new_x, new_y) == 0:
            self.player.x = new_x
            self.player.y = new_y

    def move_backward(self):
        """Move player backward."""
        dx, dy = 0, 0
        if self.player.direction == Direction.NORTH:
            dy = 1
        elif self.player.direction == Direction.SOUTH:
            dy = -1
        elif self.player.direction == Direction.EAST:
            dx = -1
        elif self.player.direction == Direction.WEST:
            dx = 1

        new_x = self.player.x + dx
        new_y = self.player.y + dy

        if self.get_tile(new_x, new_y) == 0:
            self.player.x = new_x
            self.player.y = new_y

    def turn_left(self):
        """Turn player left."""
        self.player.direction = Direction((self.player.direction - 1) % 4)

    def turn_right(self):
        """Turn player right."""
        self.player.direction = Direction((self.player.direction + 1) % 4)

    def handle_input(self) -> bool:
        """Handle keyboard input. Returns False to quit."""
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
                elif event.key == pygame.K_q:
                    self.turn_left()
                elif event.key == pygame.K_e:
                    self.turn_right()
                elif event.key == pygame.K_LEFT:
                    self.turn_left()
                elif event.key == pygame.K_RIGHT:
                    self.turn_right()

        return True

    def run(self):
        """Main game loop."""
        print("Wizardry 6 Style Dungeon Renderer")
        print("=" * 50)
        print("Controls:")
        print("  Arrow Keys: Move forward/back, turn left/right")
        print("  Q/E: Turn left/right")
        print("  ESC: Quit")
        print()
        print("Explore the dungeon!")
        print("Different wall textures show different tile types.")
        print()

        running = True
        while running:
            running = self.handle_input()
            self.render_frame()
            self.clock.tick(30)  # 30 FPS

        pygame.quit()


def main():
    """Entry point."""
    renderer = DungeonRenderer()
    renderer.run()


if __name__ == "__main__":
    main()
