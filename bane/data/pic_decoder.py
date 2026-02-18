"""Decoder for Wizardry 6 monster .PIC images.

The .PIC files contain RLE-compressed sprite data for individual monsters.
Each file decompresses to a small sprite (typically 48×68 or 64×51 pixels),
not a full-screen image.

Compression scheme (high-bit RLE):
  - 0x00: Terminator (end of compressed stream)
  - Byte with bit 7 clear (< 0x80): Read next N literal bytes
  - Byte with bit 7 set (>= 0x80): Repeat next byte (-N) times (two's complement)

After RLE decompression:
  - First 2 bytes: header length as LE16 (typically 0x0258 = 600 bytes)
  - Next header_len bytes: metadata
  - Remaining bytes: sprite pixel data in tiled planar format
"""

from __future__ import annotations

from dataclasses import dataclass
import struct

from bane.data.sprite_decoder import DEFAULT_16_PALETTE, TITLEPAG_PALETTE, Sprite, EGADecoder


PIC_DATA_SIZE = 0x5800
PIC_WIDTH = 256
PIC_HEIGHT = 176
PIC_FRAME_RECORD_SIZE = 24


@dataclass(frozen=True)
class PicHeader:
    total_size: int
    header_len: int


def _decode_rle(data: bytes) -> bytes:
    """Decode Wizardry 6 RLE compression.

    Based on the reference implementation at:
    https://github.com/kirbunkle/wizardry6PicUnpacker

    Encoding rules:
      * 0x00: Terminator (end of data)
      * Byte with bit 7 clear (< 0x80): Read next N literal bytes
      * Byte with bit 7 set (>= 0x80): Repeat next byte (-N) times (two's complement)
        Example: 0xFF = -1 = repeat 1 time, 0xFE = -2 = repeat 2 times
    
    This implementation handles concatenated RLE streams by continuing to process
    until the end of the input data.
    """
    out = bytearray()
    i = 0

    while i < len(data):
        ctrl = data[i]
        i += 1

        if ctrl == 0x00:
            # Terminator for one stream; continue to next if more data remains
            continue
        elif (ctrl & 0x80) == 0x00:
            # Positive byte: read next N literal bytes
            count = ctrl
            for _ in range(count):
                if i < len(data):
                    out.append(data[i])
                    i += 1
        else:
            # Negative byte: repeat next byte -N times (using two's complement)
            if i < len(data):
                value = data[i]
                i += 1
                # Treat ctrl as signed byte: values 128-255 represent -128 to -1
                # Repeat count is the absolute value: 256 - ctrl
                count = 256 - ctrl
                out.extend([value] * count)

    return bytes(out)


def _iter_frame_entries(
    decompressed: bytes,
    header_size: int,
) -> list[tuple[int, int, int, bytes]]:
    """Parse the 0x258-byte header into frame entries.

    Each entry is 24 bytes (12 words).
    Word 0: Offset
    Word 1: Dimensions (Low=Width, High=Height)
    Words 2-11: Bitmask (20 bytes) indicating present tiles.
    """
    entries: list[tuple[int, int, int, bytes]] = []
    record_count = header_size // PIC_FRAME_RECORD_SIZE

    for idx in range(record_count):
        start = idx * PIC_FRAME_RECORD_SIZE
        end = start + PIC_FRAME_RECORD_SIZE
        if end > len(decompressed):
            break
        
        # Read full record
        record_data = decompressed[start:end]
        words = struct.unpack("<2H", record_data[:4])
        offset = words[0]
        wh = words[1]
        mask_bytes = record_data[4:] # 20 bytes

        if offset == 0 and wh == 0:
            continue

        width_tiles = wh & 0xFF
        height_tiles = (wh >> 8) & 0xFF
        
        if width_tiles == 0 or height_tiles == 0:
            continue

        entries.append((offset, width_tiles, height_tiles, mask_bytes))

    return entries


def decode_pic_frames(
    data: bytes,
    header_skip: int | None = None,
    msb_first: bool = True,
) -> list[Sprite]:
    """Decode all frames in a .PIC file into Sprites."""
    decompressed = _decode_rle(data)
    if len(decompressed) < 2:
        raise ValueError(f"Decompressed data too short: {len(decompressed)} bytes")

    header_size = struct.unpack("<H", decompressed[:2])[0] if header_skip is None else header_skip
    if len(decompressed) < header_size:
        raise ValueError(f"Decompressed data ({len(decompressed)} bytes) < header size ({header_size} bytes)")

    entries = _iter_frame_entries(decompressed, header_size)
    frames: list[Sprite] = []

    for offset, width_tiles, height_tiles, mask_bytes in entries:
        width = width_tiles * 8
        height = height_tiles * 8
        
        # Calculate number of set bits to know payload size
        set_bits = 0
        for b in mask_bytes:
            set_bits += b.bit_count()
            
        byte_len = set_bits * 32
        
        if offset + byte_len > len(decompressed):
            continue
            
        payload = decompressed[offset:offset + byte_len]
        
        # Reconstruct full tiled planar data from sparse payload
        full_data = bytearray(width_tiles * height_tiles * 32)
        payload_ptr = 0
        
        # Tile indices in the mask are row-major (bit 0=top-left, 1=top-right, 2=next-row-left, ...)
        total_tiles = width_tiles * height_tiles
        
        for tile_idx in range(total_tiles):
            # Check bit in mask
            byte_pos = tile_idx // 8
            bit_pos = tile_idx % 8
            
            is_set = False
            if byte_pos < len(mask_bytes):
                # Assuming LSB first: Bit 0 is first tile
                if mask_bytes[byte_pos] & (1 << bit_pos):
                    is_set = True
            
            if is_set:
                if payload_ptr + 32 <= len(payload):
                    full_data[tile_idx * 32 : (tile_idx + 1) * 32] = payload[payload_ptr : payload_ptr + 32]
                    payload_ptr += 32
        
        # Tiles are stored row-major: tile 0=top-left, 1=top-right, 2=next-row-left, etc.
        decoder = EGADecoder(palette=list(TITLEPAG_PALETTE))
        sprite = decoder.decode_tiled_planar(bytes(full_data), width, height, msb_first=msb_first)
        
        frames.append(sprite)

    return frames


def _transpose_packed_to_planar_OLD(data: bytes, header_size: int = 0x258) -> bytes:
    """Transpose packed 4bpp data to tiled planar format.

    Based on the reference implementation at:
    https://github.com/kirbunkle/wizardry6PicUnpacker

    The first header_size bytes are preserved as-is.
    After that, packed 4bpp data (2 pixels per byte) is transposed into
    tiled planar format where each 32-byte block contains 4 planes of 8 bytes each.
    """
    # Preserve header
    out = bytearray(data[:header_size])

    # Transpose remaining data
    i = header_size
    read_mask = 0x80

    while i < len(data):
        j_start = len(out)
        # Reserve space for 32 bytes (4 planes * 8 bytes)
        out.extend([0] * 32)

        # Process 32 input bytes (64 pixels)
        j = j_start
        while j < j_start + 8:
            if i >= len(data):
                break

            val = data[i]
            i += 1

            # High nibble (bits 7-4) - pixel 0
            if val & 0x80: out[j + 24] |= read_mask  # bit 7 -> plane 3
            if val & 0x40: out[j + 16] |= read_mask  # bit 6 -> plane 2
            if val & 0x20: out[j + 8]  |= read_mask  # bit 5 -> plane 1
            if val & 0x10: out[j]      |= read_mask  # bit 4 -> plane 0

            read_mask >>= 1

            # Low nibble (bits 3-0) - pixel 1
            if val & 0x08: out[j + 24] |= read_mask  # bit 3 -> plane 3
            if val & 0x04: out[j + 16] |= read_mask  # bit 2 -> plane 2
            if val & 0x02: out[j + 8]  |= read_mask  # bit 1 -> plane 1
            if val & 0x01: out[j]      |= read_mask  # bit 0 -> plane 0

            read_mask >>= 1

            if read_mask == 0:
                j += 1
                read_mask = 0x80

    return bytes(out)


def decode_pic_bytes(
    data: bytes,
    width: int | None = None,
    height: int | None = None,
    layout: str = "planar-row",
    header_skip: int | None = None,
    plane_order: list[int] | None = None,
    frame_index: int = 0,
) -> Sprite:
    """Decode a .PIC file into a Sprite.

    Args:
        data: Raw RLE-compressed .PIC bytes.
        width: Sprite width in pixels (if None, auto-detect from payload size).
        height: Sprite height in pixels (if None, auto-detect from payload size).
        layout: Ignored (kept for compatibility).
        header_skip: If provided, override the header length from the file.
        plane_order: Ignored (kept for compatibility).
    """
    # Try frame table decoding first (common for monster PICs)
    frames = decode_pic_frames(data, header_skip=header_skip, msb_first=True)
    if frames:
        if frame_index < 0 or frame_index >= len(frames):
            raise IndexError(f"Frame index {frame_index} out of range (0..{len(frames) - 1})")
        return frames[frame_index]

    # Fallback to single-frame decode
    decompressed = _decode_rle(data)
    if len(decompressed) < 2:
        raise ValueError(f"Decompressed data too short: {len(decompressed)} bytes")

    header_size = struct.unpack("<H", decompressed[:2])[0] if header_skip is None else header_skip
    if len(decompressed) < header_size:
        raise ValueError(f"Decompressed data ({len(decompressed)} bytes) < header size ({header_size} bytes)")

    payload = decompressed[header_size:]

    # Auto-detect dimensions if not provided
    if width is None or height is None:
        # For tiled planar: each 32-byte tile = 64 pixels
        payload_size = len(payload)
        tiles = payload_size // 32
        total_pixels = tiles * 64

        # Try common sprite dimensions (in order of likelihood)
        candidates = [(48, 68), (64, 51), (32, 102), (96, 34), (64, 48), (68, 48), (40, 80)]
        for w, h in candidates:
            if w * h == total_pixels:
                width, height = w, h
                break

        # Fallback if no exact match
        if width is None or height is None:
            width = 64
            height = max(1, total_pixels // 64)

    # Decode from tiled planar format (row-major tile order)
    decoder = EGADecoder(palette=list(TITLEPAG_PALETTE))
    sprite = decoder.decode_tiled_planar(payload, width, height, msb_first=True)

    return sprite


def decode_pic_file(
    path: str,
    width: int | None = None,
    height: int | None = None,
    layout: str = "planar-row",
    header_skip: int | None = None,
    plane_order: list[int] | None = None,
    frame_index: int = 0,
) -> Sprite:
    """Load and decode a .PIC file from disk.

    Args:
        path: Path to the .PIC file.
        width: Sprite width (if None, auto-detect).
        height: Sprite height (if None, auto-detect).
        layout: Ignored (kept for compatibility).
        header_skip: If provided, override the header length from the file.
        plane_order: Ignored (kept for compatibility).
    """
    with open(path, "rb") as handle:
        data = handle.read()
    return decode_pic_bytes(
        data,
        width=width,
        height=height,
        layout=layout,
        header_skip=header_skip,
        plane_order=plane_order,
        frame_index=frame_index,
    )
