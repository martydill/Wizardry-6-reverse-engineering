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
# TITLEPAG.EGA (and likely all Wizardry 6 EGA images) uses a custom EGA palette
# register mapping — derived by matching T16 color-index counts against the
# reference screenshot's RGB pixel counts.  The game remaps the 16 EGA colors
# into a non-standard index order.
TITLEPAG_PALETTE: list[tuple[int, int, int]] = [
    (  0,   0,   0),  # 0:  Black
    (255, 255, 255),  # 1:  White
    ( 85,  85, 255),  # 2:  Bright Blue
    (255,  85, 255),  # 3:  Bright Magenta
    (255,  85,  85),  # 4:  Bright Red
    (255, 255,  85),  # 5:  Yellow
    ( 85, 255,  85),  # 6:  Bright Green
    ( 85, 255, 255),  # 7:  Bright Cyan
    ( 85,  85,  85),  # 8:  Dark Gray
    (170, 170, 170),  # 9:  Light Gray
    (  0,   0, 170),  # 10: Blue
    (170,   0, 170),  # 11: Magenta
    (170,   0,   0),  # 12: Red
    (170,  85,   0),  # 13: Brown
    (  0, 170,   0),  # 14: Green
    (  0, 170, 170),  # 15: Cyan
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


def decode_mazedata_tiles(path: str | Path) -> list[Sprite]:
    """Decode all wall-texture tiles from a MAZEDATA.EGA file.

    MAZEDATA.EGA stores 153 tile primitives used to assemble the 3D dungeon
    view.  The file has two sections:

    Header (0x000 – 0xA26):
        - Bytes 0-1:  N,  tile count (LE16, = 153)
        - Bytes 2-3:  N2, display-list record count (LE16, = 366)
        - Bytes 4 .. 4+N*5-1: N × 5-byte tile descriptors
        - Bytes 4+N*5 .. 4+N*5+5*N2-1: display-list table; each of the N2
          records is 4 bytes [b0, tile_id_1indexed, x_bytes, y_pixels] plus
          1 zero-byte group separator; groups of records form composite sprites

    Pixel data starts at offset 4 + N*5 + 5*N2 = 0xA27 (for the shipped file).

    Each 5-byte descriptor:
        - Bytes 0-1: segment S (LE16); absolute byte offset = S×16 + B2
        - Byte  2:   byte offset B2 within the segment (0, 4, 8, or 12)
        - Byte  3:   width_units W  (tile width = W × 8 pixels)
        - Byte  4:   height H (in pixels)

    Pixel data (offset 0x800 onward):
        Sequential planar EGA — 4 planes stored consecutively within each tile:
            Plane 0: W × H bytes
            Plane 1: W × H bytes
            Plane 2: W × H bytes
            Plane 3: W × H bytes
        Total bytes per tile = 4 × W × H

    Tiles represent the same wall face at different rendering distances/positions,
    composed by the dungeon renderer via the display-list table.
    """
    path = Path(path)
    data = path.read_bytes()

    n  = data[0] | (data[1] << 8)  # tile count (153)
    n2 = data[2] | (data[3] << 8)  # display-list record count (366)
    dl_start = 4 + n * 5
    # Display-list entries are 5 bytes each (4-byte record + 1-byte zero separator).
    # Pixel data begins immediately after the display list.
    PIXEL_DATA_OFFSET = dl_start + 5 * n2

    decoder = EGADecoder(palette=list(TITLEPAG_PALETTE))
    sprites: list[Sprite] = []

    for i in range(n):
        base = 4 + i * 5
        if base + 5 > len(data):
            break
        seg  = data[base] | (data[base + 1] << 8)
        b2   = data[base + 2]          # byte offset (0/4/8/12)
        w_units = data[base + 3]       # width / 8
        height  = data[base + 4]       # height in pixels
        abs_off  = seg * 16 + b2       # byte offset from start of pixel data
        file_off = PIXEL_DATA_OFFSET + abs_off
        width    = w_units * 8
        tile_bytes = 4 * w_units * height

        if width == 0 or height == 0:
            sprites.append(Sprite(width=8, height=8, pixels=[0] * 64, palette=list(TITLEPAG_PALETTE)))
            continue
        if file_off + tile_bytes > len(data):
            logger.warning("MAZEDATA tile %d out of bounds at 0x%05X", i, file_off)
            sprites.append(Sprite(width=width, height=height, pixels=[0] * (width * height), palette=list(TITLEPAG_PALETTE)))
            continue

        payload = data[file_off : file_off + tile_bytes]
        sprite  = decoder.decode_planar(payload, width=width, height=height, msb_first=True)
        sprites.append(sprite)

    return sprites


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

        return decoder.decode_planar(
            bytes(image_data),
            width=width,
            height=height,
            planes=4,
            msb_first=True,
            plane_order=[0, 1, 2, 3],
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
        # Font collection - decode first frame only
        decoder = EGADecoder(palette=list(DEFAULT_16_PALETTE))

        if len(data) == 1024:
            # WFONT0: 128 chars × 8 bytes = 1024. 1bpp 8×8, direct ASCII mapping.
            char_width, char_height = 8, 8
            bytes_per_char = 8
            pixels = []
            for b in data[:bytes_per_char]:
                for bit in range(7, -1, -1):
                    pixels.append(15 if (b & (1 << bit)) else 0)
        elif len(data) == 4096:
            # WFONT1-4: 128 chars × 32 bytes = 4096. 4-plane EGA 8×8.
            # Layout per char: 8 bytes plane0, 8 bytes plane1, 8 bytes plane2, 8 bytes plane3.
            # Pixel color = plane0_bit | plane1_bit<<1 | plane2_bit<<2 | plane3_bit<<3
            char_width, char_height = 8, 8
            bytes_per_char = 32
            planes = [data[p * 8 : p * 8 + 8] for p in range(4)]
            pixels = []
            for row in range(8):
                for col in range(8):
                    color = sum(((planes[p][row] >> (7 - col)) & 1) << p for p in range(4))
                    pixels.append(color)
        else:
            char_width, char_height = 8, 8
            bytes_per_char = 8
            pixels = [0] * 64

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
    elif "MAZEDATA" in path.name.upper():
        # MAZEDATA.EGA: tile atlas of 153 wall-texture primitives.
        # Header (0x000–0x7FF) contains N and 5-byte tile descriptors;
        # pixel data starts at 0x800 in sequential planar EGA format.
        frames.extend(decode_mazedata_tiles(path))
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

        if len(data) == 1024:
            # WFONT0: 128 chars × 8 bytes. 1bpp 8×8. Frame N = ASCII char N.
            char_width, char_height = 8, 8
            bytes_per_char = 8
            count = 128
            for i in range(count):
                char_data = data[i * bytes_per_char : i * bytes_per_char + bytes_per_char]
                pixels = []
                for b in char_data:
                    for bit in range(7, -1, -1):
                        pixels.append(15 if (b & (1 << bit)) else 0)
                frames.append(Sprite(width=char_width, height=char_height, pixels=pixels, palette=decoder.palette))
        elif len(data) == 4096:
            # WFONT1-4: 128 chars × 32 bytes. 4-plane EGA 8×8. Frame N = game char code N.
            # Layout per char: 8 bytes plane0, 8 bytes plane1, 8 bytes plane2, 8 bytes plane3.
            # Pixel color = plane0_bit | plane1_bit<<1 | plane2_bit<<2 | plane3_bit<<3
            char_width, char_height = 8, 8
            bytes_per_char = 32
            count = 128
            for i in range(count):
                offset = i * bytes_per_char
                planes = [data[offset + p * 8 : offset + p * 8 + 8] for p in range(4)]
                pixels = []
                for row in range(8):
                    for col in range(8):
                        color = sum(((planes[p][row] >> (7 - col)) & 1) << p for p in range(4))
                        pixels.append(color)
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
