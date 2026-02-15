"""Interactive texture mode tester for MAZEDATA.EGA.

Test different decoding and rendering approaches in real-time.
Press keys to toggle between modes and see the effect immediately.
"""

import pygame
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, Sprite, TITLEPAG_PALETTE


class TextureMode:
    """Different ways to decode and render textures."""

    # Decoding modes
    SEQUENTIAL_PLANAR = 0
    ROW_INTERLEAVED = 1

    # Plane orders
    PLANE_ORDER_0123 = [0, 1, 2, 3]
    PLANE_ORDER_3210 = [3, 2, 1, 0]
    PLANE_ORDER_0213 = [0, 2, 1, 3]
    PLANE_ORDER_3012 = [3, 0, 1, 2]

    # Rendering modes
    RENDER_FULL = 0      # Use full texture band
    RENDER_COLUMNS = 1   # Vertical columns only
    RENDER_ROWS = 2      # Horizontal rows only
    RENDER_TILED = 3     # Tile small sections
    RENDER_SCALED = 4    # Scale differently

    # Sampling modes
    SAMPLE_STRETCH = 0   # Stretch texture to fit
    SAMPLE_TILE = 1      # Tile texture
    SAMPLE_CENTER = 2    # Use center portion only


@dataclass
class RenderConfig:
    """Current rendering configuration."""
    decode_mode: int = TextureMode.SEQUENTIAL_PLANAR
    plane_order: List[int] = None
    msb_first: bool = True
    palette_id: int = 0  # 0=DEFAULT, 1=TITLEPAG, 2=Inverted, 3=Grayscale
    render_mode: int = TextureMode.RENDER_FULL
    sample_mode: int = TextureMode.SAMPLE_STRETCH
    band_height: int = 32  # 8, 16, 32, or full
    use_raw_data: bool = False  # Skip first 32KB?

    def __post_init__(self):
        if self.plane_order is None:
            self.plane_order = TextureMode.PLANE_ORDER_0123.copy()


class TextureTester:
    """Interactive texture testing application."""

    def __init__(self, width: int = 1200, height: int = 800):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("MAZEDATA Texture Mode Tester")

        # Load data
        self.raw_data = self._load_raw_data()

        # Current configuration
        self.config = RenderConfig()

        # Current band being displayed
        self.current_band = 0
        self.max_bands = 6

        # Palettes
        self.palettes = self._create_palettes()

        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 20)
        self.title_font = pygame.font.Font(None, 32)

    def _load_raw_data(self) -> bytes:
        """Load raw MAZEDATA.EGA data."""
        path = Path("gamedata/MAZEDATA.EGA")
        if not path.exists():
            print(f"Error: {path} not found")
            sys.exit(1)
        return path.read_bytes()

    def _create_palettes(self) -> List[List[Tuple[int, int, int]]]:
        """Create different palette variations to test."""
        palettes = []

        # 0: Default EGA palette
        palettes.append(list(DEFAULT_16_PALETTE))

        # 1: TITLEPAG palette
        palettes.append(list(TITLEPAG_PALETTE))

        # 2: Inverted default
        inverted = [(255-r, 255-g, 255-b) for r, g, b in DEFAULT_16_PALETTE]
        palettes.append(inverted)

        # 3: Grayscale
        grayscale = []
        for r, g, b in DEFAULT_16_PALETTE:
            gray = int(0.299 * r + 0.587 * g + 0.114 * b)
            grayscale.append((gray, gray, gray))
        palettes.append(grayscale)

        # 4: High contrast
        high_contrast = []
        for i in range(16):
            val = (i * 17)  # 0, 17, 34, ..., 255
            high_contrast.append((val, val, val))
        palettes.append(high_contrast)

        return palettes

    def decode_texture(self) -> Sprite:
        """Decode texture with current configuration."""
        # Select data range
        if self.config.use_raw_data:
            # Try using the extra 70KB data
            data = self.raw_data[32000:32000 + 32000]
        else:
            data = self.raw_data[:32000]

        # Get palette
        palette = self.palettes[self.config.palette_id]

        # Create decoder
        decoder = EGADecoder(palette=palette)

        # Decode based on mode
        try:
            if self.config.decode_mode == TextureMode.SEQUENTIAL_PLANAR:
                sprite = decoder.decode_planar(
                    data,
                    width=320,
                    height=200,
                    msb_first=self.config.msb_first,
                    plane_order=self.config.plane_order
                )
            else:  # ROW_INTERLEAVED
                sprite = decoder.decode_planar_row_interleaved(
                    data,
                    width=320,
                    height=200,
                    msb_first=self.config.msb_first,
                    plane_order=self.config.plane_order
                )
            return sprite
        except Exception as e:
            print(f"Decode error: {e}")
            # Return blank sprite on error
            return Sprite(width=320, height=200, pixels=[0]*64000, palette=palette)

    def extract_band(self, atlas: Sprite, band_id: int) -> Sprite:
        """Extract a texture band from the atlas."""
        band_height = self.config.band_height

        # Calculate band position
        y_start = band_id * band_height
        y_end = min(y_start + band_height, atlas.height)

        if y_start >= atlas.height:
            # Return blank if out of range
            return Sprite(width=atlas.width, height=band_height,
                         pixels=[0]*(atlas.width*band_height), palette=atlas.palette)

        # Extract pixels
        pixels = []
        for y in range(y_start, y_end):
            for x in range(atlas.width):
                pixels.append(atlas.get_pixel(x, y))

        # Pad if needed
        actual_height = y_end - y_start
        while len(pixels) < atlas.width * band_height:
            pixels.append(0)

        return Sprite(width=atlas.width, height=actual_height,
                     pixels=pixels, palette=atlas.palette)

    def render_texture(self, texture: Sprite, x: int, y: int, width: int, height: int):
        """Render texture with current rendering mode."""
        mode = self.config.render_mode

        if mode == TextureMode.RENDER_FULL:
            self._render_full(texture, x, y, width, height)
        elif mode == TextureMode.RENDER_COLUMNS:
            self._render_columns(texture, x, y, width, height)
        elif mode == TextureMode.RENDER_ROWS:
            self._render_rows(texture, x, y, width, height)
        elif mode == TextureMode.RENDER_TILED:
            self._render_tiled(texture, x, y, width, height)
        elif mode == TextureMode.RENDER_SCALED:
            self._render_scaled(texture, x, y, width, height)

    def _render_full(self, texture: Sprite, x: int, y: int, width: int, height: int):
        """Render full texture stretched to fit."""
        surface = pygame.Surface((texture.width, texture.height))
        for py in range(texture.height):
            for px in range(texture.width):
                color_idx = texture.get_pixel(px, py)
                if 0 <= color_idx < len(texture.palette):
                    surface.set_at((px, py), texture.palette[color_idx])

        # Scale to fit
        scaled = pygame.transform.scale(surface, (width, height))
        self.screen.blit(scaled, (x, y))

    def _render_columns(self, texture: Sprite, x: int, y: int, width: int, height: int):
        """Render vertical columns sampled from texture."""
        # Sample vertical columns at regular intervals
        num_columns = 32
        column_width = width // num_columns

        for i in range(num_columns):
            # Sample column from texture
            tex_x = (i * texture.width) // num_columns

            for py in range(height):
                tex_y = (py * texture.height) // height
                color_idx = texture.get_pixel(tex_x, tex_y)
                if 0 <= color_idx < len(texture.palette):
                    color = texture.palette[color_idx]
                    pygame.draw.rect(self.screen, color,
                                   (x + i * column_width, y + py, column_width, 1))

    def _render_rows(self, texture: Sprite, x: int, y: int, width: int, height: int):
        """Render horizontal rows sampled from texture."""
        for py in range(height):
            # Sample one row from texture
            tex_y = (py * texture.height) // height

            for px in range(width):
                tex_x = (px * texture.width) // width
                color_idx = texture.get_pixel(tex_x, tex_y)
                if 0 <= color_idx < len(texture.palette):
                    self.screen.set_at((x + px, y + py), texture.palette[color_idx])

    def _render_tiled(self, texture: Sprite, x: int, y: int, width: int, height: int):
        """Render texture tiled."""
        tile_w = min(64, texture.width)
        tile_h = min(64, texture.height)

        for ty in range(0, height, tile_h):
            for tx in range(0, width, tile_w):
                for py in range(min(tile_h, height - ty)):
                    for px in range(min(tile_w, width - tx)):
                        tex_x = px % texture.width
                        tex_y = py % texture.height
                        color_idx = texture.get_pixel(tex_x, tex_y)
                        if 0 <= color_idx < len(texture.palette):
                            self.screen.set_at((x + tx + px, y + ty + py),
                                             texture.palette[color_idx])

    def _render_scaled(self, texture: Sprite, x: int, y: int, width: int, height: int):
        """Render with different scaling approach."""
        # Render at 2x or 4x scale then scale down
        scale = 4
        temp_surface = pygame.Surface((texture.width * scale, texture.height * scale))

        for py in range(texture.height):
            for px in range(texture.width):
                color_idx = texture.get_pixel(px, py)
                if 0 <= color_idx < len(texture.palette):
                    color = texture.palette[color_idx]
                    pygame.draw.rect(temp_surface, color,
                                   (px * scale, py * scale, scale, scale))

        scaled = pygame.transform.scale(temp_surface, (width, height))
        self.screen.blit(scaled, (x, y))

    def render_frame(self):
        """Render the current frame."""
        self.screen.fill((20, 20, 20))

        # Decode full atlas
        atlas = self.decode_texture()

        # Extract current band
        band = self.extract_band(atlas, self.current_band)

        # Main texture display (large)
        main_w, main_h = 800, 400
        main_x, main_y = 50, 150
        pygame.draw.rect(self.screen, (40, 40, 40), (main_x-2, main_y-2, main_w+4, main_h+4), 2)
        self.render_texture(band, main_x, main_y, main_w, main_h)

        # Small preview of full atlas
        preview_w, preview_h = 320, 200
        preview_x, preview_y = 870, 150
        pygame.draw.rect(self.screen, (40, 40, 40), (preview_x-2, preview_y-2, preview_w+4, preview_h+4), 2)

        # Render full atlas preview
        for py in range(preview_h):
            for px in range(preview_w):
                color_idx = atlas.get_pixel(px, py)
                if 0 <= color_idx < len(atlas.palette):
                    self.screen.set_at((preview_x + px, preview_y + py),
                                     atlas.palette[color_idx])

        # Highlight current band on preview
        band_y = self.current_band * self.config.band_height
        pygame.draw.rect(self.screen, (255, 255, 0),
                        (preview_x, preview_y + band_y, preview_w, self.config.band_height), 2)

        # Draw UI
        self._draw_ui()

        pygame.display.flip()

    def _draw_ui(self):
        """Draw UI overlay with current settings."""
        # Title
        title = self.title_font.render("MAZEDATA Texture Mode Tester", True, (255, 255, 255))
        self.screen.blit(title, (50, 20))

        # Current settings
        y = 80
        settings = [
            f"Band: {self.current_band}/{self.max_bands-1} (Height: {self.config.band_height}px)",
            f"Decode: {'Sequential' if self.config.decode_mode == 0 else 'Row-Interleaved'}",
            f"Plane Order: {self.config.plane_order}",
            f"Bit Order: {'MSB-first' if self.config.msb_first else 'LSB-first'}",
            f"Palette: {['Default', 'TitlePag', 'Inverted', 'Grayscale', 'High-Contrast'][self.config.palette_id]}",
            f"Render: {['Full', 'Columns', 'Rows', 'Tiled', 'Scaled'][self.config.render_mode]}",
            f"Data: {'Extra 70KB' if self.config.use_raw_data else 'Main 32KB'}",
        ]

        for setting in settings:
            text = self.font.render(setting, True, (200, 200, 200))
            self.screen.blit(text, (50, y))
            y += 22

        # Controls
        y = 580
        controls = [
            "Controls:",
            "  [/] - Change band | 1-5 - Band height (8/16/32/64/200)",
            "  D - Toggle decode mode | B - Toggle bit order",
            "  P - Cycle plane order | C - Cycle palette",
            "  R - Cycle render mode | X - Toggle data source",
            "  SPACE - Reset to defaults | ESC - Quit",
        ]

        for control in controls:
            text = self.font.render(control, True, (150, 150, 150))
            self.screen.blit(text, (50, y))
            y += 20

    def handle_input(self) -> bool:
        """Handle keyboard input."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False

                # Band selection
                elif event.key == pygame.K_LEFTBRACKET:
                    self.current_band = (self.current_band - 1) % self.max_bands
                elif event.key == pygame.K_RIGHTBRACKET:
                    self.current_band = (self.current_band + 1) % self.max_bands

                # Band height
                elif event.key == pygame.K_1:
                    self.config.band_height = 8
                    self.max_bands = 25
                elif event.key == pygame.K_2:
                    self.config.band_height = 16
                    self.max_bands = 12
                elif event.key == pygame.K_3:
                    self.config.band_height = 32
                    self.max_bands = 6
                elif event.key == pygame.K_4:
                    self.config.band_height = 64
                    self.max_bands = 3
                elif event.key == pygame.K_5:
                    self.config.band_height = 200
                    self.max_bands = 1

                # Decode mode
                elif event.key == pygame.K_d:
                    self.config.decode_mode = 1 - self.config.decode_mode

                # Bit order
                elif event.key == pygame.K_b:
                    self.config.msb_first = not self.config.msb_first

                # Plane order
                elif event.key == pygame.K_p:
                    orders = [
                        [0, 1, 2, 3],
                        [3, 2, 1, 0],
                        [0, 2, 1, 3],
                        [3, 0, 1, 2],
                        [1, 0, 3, 2],
                        [2, 3, 0, 1],
                    ]
                    try:
                        idx = orders.index(self.config.plane_order)
                        self.config.plane_order = orders[(idx + 1) % len(orders)]
                    except ValueError:
                        self.config.plane_order = orders[0]

                # Palette
                elif event.key == pygame.K_c:
                    self.config.palette_id = (self.config.palette_id + 1) % len(self.palettes)

                # Render mode
                elif event.key == pygame.K_r:
                    self.config.render_mode = (self.config.render_mode + 1) % 5

                # Data source
                elif event.key == pygame.K_x:
                    self.config.use_raw_data = not self.config.use_raw_data

                # Reset
                elif event.key == pygame.K_SPACE:
                    self.config = RenderConfig()
                    self.current_band = 0

        return True

    def run(self):
        """Main loop."""
        print("MAZEDATA Texture Mode Tester")
        print("=" * 60)
        print("Press keys to toggle different decoding/rendering modes")
        print("Use [/] to change bands")
        print()

        running = True
        while running:
            running = self.handle_input()
            self.render_frame()
            self.clock.tick(30)

        pygame.quit()


def main():
    tester = TextureTester()
    tester.run()


if __name__ == "__main__":
    main()
