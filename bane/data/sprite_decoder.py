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
    - Plane 3: bit 3 (intensity)

    Each plane stores 1 bit per pixel, packed 8 pixels per byte.
    For a 320x200 image, each plane is 320*200/8 = 8000 bytes.
    Total: 4 * 8000 = 32000 bytes.
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
        """Decode interleaved planar EGA data into a Sprite.

        Args:
            data: Raw planar byte data
            width: Image width in pixels (must be multiple of 8)
            height: Image height in pixels
            planes: Number of bit planes (typically 4 for EGA)
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
    """Decode a full-screen .EGA file (e.g., TITLEPAG.EGA).

    These files are typically 32768 bytes, consisting of 4 planes of 8192 bytes each.
    Each 8192-byte block contains:
    - 8000 bytes of image data (320x200 1bpp)
    - 192 bytes of padding/palette data
    """
    path = Path(path)
    data = path.read_bytes()

    if len(data) != 32768:
        # Fallback for non-standard EGA files (like fonts)
        return Sprite(0, 0, [], [])

    width, height = 320, 200
    pixels = [0] * (width * height)
    bytes_per_row = width // 8
    
    # Image data consists of 4 planes of 8000 bytes each, starting at 8k boundaries.
    # The plane order in Wiz6 .EGA files maps to bit positions as follows:
    # Plane 0 -> Bit 2 (Red)
    # Plane 1 -> Bit 0 (Blue)
    # Plane 2 -> Bit 1 (Green)
    # Plane 3 -> Bit 3 (Intensity)
    plane_to_bit = {0: 2, 1: 0, 2: 1, 3: 3}

    header_data = bytearray()
    for plane in range(4):
        plane_base = plane * 8192
        bit_pos = plane_to_bit[plane]
        header_data.extend(data[plane_base + 8000 : plane_base + 8192])
        
        for y in range(height):
            row_base = plane_base + y * bytes_per_row
            for bx in range(bytes_per_row):
                byte_val = data[row_base + bx]
                for bit in range(8):
                    x = bx * 8 + (7 - bit)
                    if byte_val & (1 << bit):
                        pixels[y * width + x] |= (1 << bit_pos)

    # Extract palette from the aggregated tail data
    palette = []
    has_palette = False
    for i in range(16):
        r = header_data[i * 3]
        g = header_data[i * 3 + 1]
        b = header_data[i * 3 + 2]
        if r != 0 or g != 0 or b != 0:
            has_palette = True
        palette.append((r, g, b))

    if not has_palette:
        palette = list(DEFAULT_16_PALETTE)

    return Sprite(width, height, pixels, palette)


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
