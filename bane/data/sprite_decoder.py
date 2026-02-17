"""EGA sprite decoder for Wizardry 6 graphics.

Wizardry 6 uses EGA (Enhanced Graphics Adapter) graphics:
- Resolution: 320x200 pixels
- Color depth: 16 colors from EGA's 64-color palette
- Storage: Planar format — 4 bit planes per pixel
  (4 planes × 1 bit = 16 possible colors per pixel)

EGA Palette:
- 64 total colors using RGBI encoding (Red, Green, Blue, Intensity channels)
- Each channel has 2 levels (on/off), with Intensity providing a brightness boost
- The default CGA-compatible 16-color palette is the most common
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# EGA 64-color master palette (RGBI encoding)
# Each color has 6 bits: xxRGBrgb where uppercase = high bits, lowercase = low bits
# This is the full 64-color EGA palette as RGB888 tuples.
# ---------------------------------------------------------------------------
EGA_64_PALETTE: list[tuple[int, int, int]] = []

# Generate the 64-color EGA palette
# Bits: r g b R G B  (bit 5 is r, bit 0 is B)
# Mapping for 6-bit value i:
# Bit 0: B (blue high)
# Bit 1: G (green high)
# Bit 2: R (red high)
# Bit 3: b (blue low)
# Bit 4: g (green low)
# Bit 5: r (red low)
for i in range(64):
    B = (i >> 0) & 1
    G = (i >> 1) & 1
    R = (i >> 2) & 1
    b = (i >> 3) & 1
    g = (i >> 4) & 1
    r = (i >> 5) & 1
    rv = R * 0xAA + r * 0x55
    gv = G * 0xAA + g * 0x55
    bv = B * 0xAA + b * 0x55
    EGA_64_PALETTE.append((rv, gv, bv))


# ---------------------------------------------------------------------------
# Default CGA-compatible 16-color palette (indices into EGA 64-color palette)
# This is what Wizardry 6 most likely uses.
# ---------------------------------------------------------------------------
DEFAULT_16_PALETTE_INDICES = [
    0,   # 0: Black (000000)
    1,   # 1: Blue (000001)
    2,   # 2: Green (000010)
    3,   # 3: Cyan (000011)
    4,   # 4: Red (000100)
    5,   # 5: Magenta (000101)
    20,  # 6: Brown (010100) - Special case for color 6
    7,   # 7: Light gray (000111)
    56,  # 8: Dark gray (111000)
    57,  # 9: Light blue (111001)
    58,  # 10: Light green (111010)
    59,  # 11: Light cyan (111011)
    60,  # 12: Light red (111100)
    61,  # 13: Light magenta (111101)
    62,  # 14: Yellow (111110)
    63,  # 15: White (111111)
]

DEFAULT_16_PALETTE: list[tuple[int, int, int]] = [
    EGA_64_PALETTE[i] for i in DEFAULT_16_PALETTE_INDICES
]

# Wizardry 6 TITLEPAG.EGA custom palette (extracted from reference screenshot)
# Uses VGA DAC encoding: 6-bit values (0-63) × 4 = 8-bit (0, 84, 168, 252)
TITLEPAG_PALETTE: list[tuple[int, int, int]] = [
    (  0,   0,   0),  # 0: Black
    ( 84,  84,  84),  # 1: Dark gray
    (168, 168, 168),  # 2: Light gray
    (252, 252, 252),  # 3: White
    (168,   0,   0),  # 4: Red
    (168,  84,   0),  # 5: Brown
    (252, 252,  84),  # 6: Yellow
    ( 84, 252, 252),  # 7: Light cyan
    (  0, 168,   0),  # 8: Green
    (168,   0, 168),  # 9: Magenta
    (252,  84, 252),  # 10: Light magenta
    (252,  84,  84),  # 11: Light red
    ( 84, 252,  84),  # 12: Light green
    (  0,   0, 168),  # 13: Blue
    (  0, 168, 168),  # 14: Cyan
    ( 84,  84, 252),  # 15: Light blue
]


@dataclass
class Sprite:
    """A decoded sprite/image."""

    width: int = 0
    height: int = 0
    pixels: list[int] = field(default_factory=list)  # palette indices (0-15)
    palette: list[tuple[int, int, int]] = field(default_factory=list)  # RGB tuples

    @property
    def pixel_count(self) -> int:
        return self.width * self.height

    def get_pixel(self, x: int, y: int) -> int:
        """Get palette index at (x, y)."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.pixels[y * self.width + x]
        return 0

    def get_rgb(self, x: int, y: int) -> tuple[int, int, int]:
        """Get RGB color at (x, y)."""
        idx = self.get_pixel(x, y)
        if 0 <= idx < len(self.palette):
            return self.palette[idx]
        return (0, 0, 0)

    def to_rgba_bytes(self, transparent_index: int = -1) -> bytes:
        """Convert to RGBA bytes suitable for creating a pygame surface or PIL image."""
        result = bytearray(self.width * self.height * 4)
        for i, idx in enumerate(self.pixels):
            offset = i * 4
            if idx == transparent_index:
                result[offset:offset + 4] = b"\x00\x00\x00\x00"
            elif 0 <= idx < len(self.palette):
                r, g, b = self.palette[idx]
                result[offset] = r
                result[offset + 1] = g
                result[offset + 2] = b
                result[offset + 3] = 255
        return bytes(result)

    def to_rgb_bytes(self) -> bytes:
        """Convert to RGB bytes."""
        result = bytearray(self.width * self.height * 3)
        for i, idx in enumerate(self.pixels):
            offset = i * 3
            if 0 <= idx < len(self.palette):
                r, g, b = self.palette[idx]
                result[offset] = r
                result[offset + 1] = g
                result[offset + 2] = b
        return bytes(result)

    def scale(self, factor: int) -> Sprite:
        """Create a scaled copy using nearest-neighbor interpolation."""
        new_w = self.width * factor
        new_h = self.height * factor
        new_pixels: list[int] = []
        for y in range(new_h):
            src_y = y // factor
            for x in range(new_w):
                src_x = x // factor
                new_pixels.append(self.pixels[src_y * self.width + src_x])
        return Sprite(
            width=new_w,
            height=new_h,
            pixels=new_pixels,
            palette=list(self.palette),
        )


class EGADecoder:
    """Decodes EGA planar graphics into Sprite objects.

    EGA planar format stores pixels across 4 bit planes:
    - Plane 0: bit 0 of each pixel's color index
    - Plane 1: bit 1
    - Plane 2: bit 2
    - Plane 3: bit 3

    Each plane stores 1 bit per pixel, packed 8 pixels per byte (MSB first).
    For a 320x200 image, each plane is 320*200/8 = 8000 bytes.
    Total: 4 * 8000 = 32000 bytes.

    Wizardry 6 uses two planar storage formats:
    1. Sequential planar (MAZEDATA.EGA, TITLEPAG.EGA): Each plane stored completely
       before the next (plane0, plane1, plane2, plane3)
    2. Row-interleaved planar (some .PIC files): Planes interleaved per scanline
       (plane0_row0, plane1_row0, plane2_row0, plane3_row0, plane0_row1, ...)

    Many .EGA files have a 768-byte VGA palette header before the image data.
    MAZEDATA.EGA has NO palette header - use DEFAULT_16_PALETTE.
    """

    def __init__(self, palette: list[tuple[int, int, int]] | None = None) -> None:
        self.palette = palette or list(DEFAULT_16_PALETTE)

    def decode_planar(
        self,
        data: bytes,
        width: int,
        height: int,
        planes: int = 4,
        msb_first: bool = True,
        plane_order: list[int] | None = None,
    ) -> Sprite:
        """Decode sequential planar EGA data into a Sprite.

        Sequential planar format stores each complete plane consecutively:
        - Plane 0: all bytes for this plane
        - Plane 1: all bytes for this plane
        - Plane 2: all bytes for this plane
        - Plane 3: all bytes for this plane

        Args:
            data: Raw planar byte data
            width: Image width in pixels (must be multiple of 8)
            height: Image height in pixels
            planes: Number of bit planes (typically 4 for EGA)
            msb_first: If True, MSB is leftmost pixel in each byte (default for EGA)
            plane_order: Optional custom plane ordering (default [0,1,2,3])
        """
        if width % 8 != 0:
            raise ValueError(f"Width must be multiple of 8, got {width}")

        bytes_per_row = width // 8
        plane_size = bytes_per_row * height
        expected_size = plane_size * planes

        if len(data) < expected_size:
            logger.warning(
                "Planar data too short: expected %d bytes, got %d",
                expected_size,
                len(data),
            )
            # Pad with zeros
            data = data + b"\x00" * (expected_size - len(data))

        pixels: list[int] = [0] * (width * height)

        order = plane_order or list(range(planes))
        if len(order) != planes:
            raise ValueError("plane_order must match number of planes")

        for plane_index, plane in enumerate(order):
            plane_offset = plane_index * plane_size
            for y in range(height):
                row_offset = plane_offset + y * bytes_per_row
                for byte_idx in range(bytes_per_row):
                    byte_val = data[row_offset + byte_idx]
                    for bit in range(8):
                        if msb_first:
                            x = byte_idx * 8 + (7 - bit)
                        else:
                            x = byte_idx * 8 + bit
                        pixel_idx = y * width + x
                        if byte_val & (1 << bit):
                            pixels[pixel_idx] |= 1 << plane

        return Sprite(
            width=width,
            height=height,
            pixels=pixels,
            palette=list(self.palette),
        )

    def decode_planar_row_interleaved(
        self,
        data: bytes,
        width: int,
        height: int,
        planes: int = 4,
        msb_first: bool = True,
        plane_order: list[int] | None = None,
    ) -> Sprite:
        """Decode EGA planar data where planes are interleaved per scanline.

        Layout per row:
            plane0_row, plane1_row, plane2_row, plane3_row
        Each row segment is width/8 bytes per plane.
        """
        if width % 8 != 0:
            raise ValueError(f"Width must be multiple of 8, got {width}")

        bytes_per_row = width // 8
        row_size = bytes_per_row * planes
        expected_size = row_size * height

        if len(data) < expected_size:
            logger.warning(
                "Planar row data too short: expected %d bytes, got %d",
                expected_size,
                len(data),
            )
            data = data + b"\x00" * (expected_size - len(data))

        pixels: list[int] = [0] * (width * height)

        order = plane_order or list(range(planes))
        if len(order) != planes:
            raise ValueError("plane_order must match number of planes")

        for y in range(height):
            row_base = y * row_size
            for plane_index, plane in enumerate(order):
                plane_offset = row_base + plane_index * bytes_per_row
                for byte_idx in range(bytes_per_row):
                    byte_val = data[plane_offset + byte_idx]
                    for bit in range(8):
                        if msb_first:
                            x = byte_idx * 8 + (7 - bit)
                        else:
                            x = byte_idx * 8 + bit
                        pixel_idx = y * width + x
                        if byte_val & (1 << bit):
                            pixels[pixel_idx] |= 1 << plane

        return Sprite(
            width=width,
            height=height,
            pixels=pixels,
            palette=list(self.palette),
        )

    def decode_linear(self, data: bytes, width: int, height: int) -> Sprite:
        """Decode linear (non-planar) 4-bit packed pixel data.

        Each byte contains two pixels: high nibble first, low nibble second.
        """
        pixels: list[int] = []
        for byte_val in data:
            pixels.append((byte_val >> 4) & 0x0F)
            pixels.append(byte_val & 0x0F)

        # Trim to exact pixel count
        pixel_count = width * height
        pixels = pixels[:pixel_count]

        # Pad if too short
        while len(pixels) < pixel_count:
            pixels.append(0)

        return Sprite(
            width=width,
            height=height,
            pixels=pixels,
            palette=list(self.palette),
        )

    def decode_tiled_planar(
        self,
        data: bytes,
        width: int,
        height: int,
        plane_order: list[int] | None = None,
        msb_first: bool = True,
        row_major: bool = True,
    ) -> Sprite:
        """Decode EGA tiled planar format (used by WPORT and monster .PIC files).

        Each 32-byte block is one 8x8 tile:
          - Bytes 0-7: plane 0 (bit 0 of color)
          - Bytes 8-15: plane 1 (bit 1 of color)
          - Bytes 16-23: plane 2 (bit 2 of color)
          - Bytes 24-31: plane 3 (bit 3 of color)
        
        Args:
            data: Raw tiled planar byte data
            width: Image width in pixels (must be multiple of 8)
            height: Image height in pixels (must be multiple of 8)
            plane_order: Optional custom plane ordering (default [0,1,2,3])
            msb_first: If True, MSB is leftmost pixel in each byte
            row_major: If True, tiles are stored left-to-right, then top-to-bottom
        """
        if width % 8 != 0 or height % 8 != 0:
            raise ValueError(f"Tiled planar decode requires 8x8 alignment, got {width}x{height}")

        tiles_x = width // 8
        tiles_y = height // 8
        expected_tiles = tiles_x * tiles_y
        expected_bytes = expected_tiles * 32
        
        if len(data) < expected_bytes:
            data = data + b"\x00" * (expected_bytes - len(data))

        pixels = [0] * (width * height)
        order = plane_order or [0, 1, 2, 3]
        
        for tile_idx in range(expected_tiles):
            tile_base = tile_idx * 32
            if row_major:
                tile_x = tile_idx % tiles_x
                tile_y = tile_idx // tiles_x
            else:
                tile_x = tile_idx // tiles_y
                tile_y = tile_idx % tiles_y

            for row in range(8):
                for bit in range(8):
                    if msb_first:
                        mask = 0x80 >> bit
                    else:
                        mask = 1 << bit
                    
                    color = 0
                    for plane_idx, target_plane in enumerate(order):
                        if data[tile_base + row + plane_idx * 8] & mask:
                            color |= (1 << target_plane)

                    px = tile_x * 8 + bit
                    py = tile_y * 8 + row
                    pixels[py * width + px] = color

        return Sprite(
            width=width,
            height=height,
            pixels=pixels,
            palette=list(self.palette),
        )

    def decode_byte_per_pixel(self, data: bytes, width: int, height: int) -> Sprite:
        """Decode data where each byte is a single palette index."""
        pixel_count = width * height
        pixels = list(data[:pixel_count])
        while len(pixels) < pixel_count:
            pixels.append(0)

        # Clamp to valid palette range
        pixels = [p & 0x0F for p in pixels]

        return Sprite(
            width=width,
            height=height,
            pixels=pixels,
            palette=list(self.palette),
        )

    def set_palette_from_ega_registers(self, registers: list[int]) -> None:
        """Set the 16-color palette from EGA palette register values.

        Each register value is an index (0-63) into the EGA 64-color master palette.
        """
        self.palette = [
            EGA_64_PALETTE[reg & 0x3F] for reg in registers[:16]
        ]
        # Pad if fewer than 16
        while len(self.palette) < 16:
            self.palette.append((0, 0, 0))


def decode_ega_file(path: str | Path) -> Sprite:
    """Decode an .EGA file.

    Handles full-screen 320x200 images (32768 bytes) and 
    character portrait collections (4096 bytes).
    """
    path = Path(path)
    data = path.read_bytes()

    if len(data) == 32768:
        # Full-screen sequential planar (e.g. TITLEPAG.EGA)
        # Format: 4 planes × 8192 bytes = 32768 bytes (each plane is 8000 bytes + 192 padding)
        # No embedded palette — use the known-good custom palette.
        decoder = EGADecoder(palette=TITLEPAG_PALETTE)
        width, height = 320, 200
        bytes_per_plane_data = width * height // 8  # 8000 bytes
        image_data = bytearray()

        for plane in range(4):
            plane_start = plane * 8192
            image_data.extend(data[plane_start : plane_start + bytes_per_plane_data])

        # Wizardry 6 plane ordering found through testing
        return decoder.decode_planar(
            bytes(image_data),
            width=width,
            height=height,
            planes=4,
            msb_first=True,
            plane_order=[3, 0, 2, 1],
        )
    elif len(data) == 4096 and "WPORT" in path.name.upper():
        # Character portrait collection
        # 14 portraits of 24x24 tiled planar (14 * 288 = 4032 bytes)
        decoder = EGADecoder(palette=list(DEFAULT_16_PALETTE))
        return decoder.decode_tiled_planar(
            data[:288],
            width=24,
            height=24,
        )
    elif "WFONT" in path.name.upper():
        # Font collection
        decoder = EGADecoder(palette=list(DEFAULT_16_PALETTE))
        
        # Determine char size based on file size
        if len(data) == 4096: # WFONT1, WFONT2...
            # 256 chars * 16 bytes = 4096. 8x16 1bpp.
            char_width, char_height = 8, 16
        elif len(data) == 1024: # WFONT0
            # 128 chars * 8 bytes = 1024. 8x8 1bpp.
            char_width, char_height = 8, 8
        else:
            # Unknown, default to 8x8 and read what we can
            char_width, char_height = 8, 8
            
        bytes_per_char = (char_width * char_height) // 8
        pixels = []
        char_data = data[:bytes_per_char]
        for b in char_data:
            for bit in range(7, -1, -1):
                pixels.append(15 if (b & (1 << bit)) else 0)
        return Sprite(width=char_width, height=char_height, pixels=pixels, palette=decoder.palette)
    else:
        # Fallback/Unknown
        logger.warning(f"Unknown EGA file format: {path.name} ({len(data)} bytes)")
        return Sprite(width=32, height=32, pixels=[0]*(32*32), palette=list(DEFAULT_16_PALETTE))


def decode_ega_frames(path: str | Path) -> list[Sprite]:
    """Decode all frames from an .EGA collection file."""
    path = Path(path)
    data = path.read_bytes()
    frames: list[Sprite] = []

    if len(data) == 32768:
        # Single full-screen image with 8192-byte plane stride (TITLEPAG, DRAGONSC, etc.)
        frames.append(decode_ega_file(path))
    elif len(data) >= 32000:
        # MAZEDATA.EGA style: multiple sequential 32000-byte images, no palette header
        offset = 0
        while offset + 32000 <= len(data):
            decoder = EGADecoder(palette=list(DEFAULT_16_PALETTE))
            frames.append(decoder.decode_planar(
                data[offset : offset + 32000],
                width=320,
                height=200,
                msb_first=True
            ))
            offset += 32000
    elif len(data) == 4096 and "WPORT" in path.name.upper():
        decoder = EGADecoder(palette=list(DEFAULT_16_PALETTE))
        # 14 frames of 24x24 tiled planar (288 bytes each)
        for i in range(14):
            offset = i * 288
            frames.append(
                decoder.decode_tiled_planar(
                    data[offset : offset + 288],
                    width=24,
                    height=24,
                )
            )
    elif "WFONT" in path.name.upper():
        decoder = EGADecoder(palette=list(DEFAULT_16_PALETTE))
        
        if len(data) == 4096:
            char_width, char_height = 8, 16
            count = 256
        elif len(data) == 1024:
            char_width, char_height = 8, 8
            count = 128
        else:
            char_width, char_height = 8, 8
            count = len(data) // 8

        bytes_per_char = (char_width * char_height) // 8
        
        for i in range(count):
            offset = i * bytes_per_char
            if offset + bytes_per_char > len(data):
                break
            char_data = data[offset : offset + bytes_per_char]
            pixels = []
            for b in char_data:
                for bit in range(7, -1, -1):
                    pixels.append(15 if (b & (1 << bit)) else 0)
            frames.append(Sprite(width=char_width, height=char_height, pixels=pixels, palette=decoder.palette))
    
    return frames


class SpriteAtlas:
    """Manages a collection of sprites extracted from game data.

    The sprite atlas index within SCENARIO.DBS maps sprite IDs to their
    location and dimensions in the packed sprite data.
    """

    def __init__(self) -> None:
        self._sprites: dict[int, Sprite] = {}

    def add_sprite(self, sprite_id: int, sprite: Sprite) -> None:
        self._sprites[sprite_id] = sprite

    def get_sprite(self, sprite_id: int) -> Sprite | None:
        return self._sprites.get(sprite_id)

    @property
    def sprite_ids(self) -> list[int]:
        return sorted(self._sprites.keys())

    @property
    def count(self) -> int:
        return len(self._sprites)

    def __contains__(self, sprite_id: int) -> bool:
        return sprite_id in self._sprites

    def __len__(self) -> int:
        return len(self._sprites)
