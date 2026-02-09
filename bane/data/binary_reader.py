"""Binary file reader with little-endian support and bounds checking.

This is the foundational utility for parsing all original Wizardry 6 data files.
All original files use little-endian byte ordering.
"""

from __future__ import annotations

import struct
from pathlib import Path


class BinaryReaderError(Exception):
    """Raised when a binary read operation fails."""


class BinaryReader:
    """Reads binary data from a file or bytes buffer with bounds checking.

    Supports little-endian integer reads, string reads, seeking, and
    sub-reader creation for parsing nested data structures.
    """

    def __init__(self, data: bytes, name: str = "<buffer>") -> None:
        self._data = data
        self._pos = 0
        self._name = name

    @classmethod
    def from_file(cls, path: Path | str) -> BinaryReader:
        """Create a BinaryReader from a file path."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")
        data = path.read_bytes()
        return cls(data, name=str(path))

    @property
    def position(self) -> int:
        """Current read position."""
        return self._pos

    @property
    def size(self) -> int:
        """Total size of the data buffer."""
        return len(self._data)

    @property
    def remaining(self) -> int:
        """Number of bytes remaining from current position."""
        return max(0, len(self._data) - self._pos)

    @property
    def at_end(self) -> bool:
        """True if the reader is at or past the end."""
        return self._pos >= len(self._data)

    def _check_bounds(self, count: int) -> None:
        if self._pos + count > len(self._data):
            raise BinaryReaderError(
                f"Read of {count} bytes at offset 0x{self._pos:X} exceeds "
                f"buffer size 0x{len(self._data):X} in {self._name}"
            )

    def seek(self, offset: int) -> None:
        """Seek to an absolute position."""
        if offset < 0 or offset > len(self._data):
            raise BinaryReaderError(
                f"Seek to 0x{offset:X} out of range [0, 0x{len(self._data):X}] "
                f"in {self._name}"
            )
        self._pos = offset

    def skip(self, count: int) -> None:
        """Skip forward by count bytes."""
        self._check_bounds(count)
        self._pos += count

    def read_bytes(self, count: int) -> bytes:
        """Read exactly count raw bytes."""
        self._check_bounds(count)
        data = self._data[self._pos : self._pos + count]
        self._pos += count
        return data

    def peek_bytes(self, count: int) -> bytes:
        """Read count bytes without advancing position."""
        self._check_bounds(count)
        return self._data[self._pos : self._pos + count]

    def read_u8(self) -> int:
        """Read an unsigned 8-bit integer."""
        self._check_bounds(1)
        val = self._data[self._pos]
        self._pos += 1
        return val

    def read_i8(self) -> int:
        """Read a signed 8-bit integer."""
        self._check_bounds(1)
        val = struct.unpack_from("<b", self._data, self._pos)[0]
        self._pos += 1
        return val

    def read_u16(self) -> int:
        """Read an unsigned 16-bit little-endian integer."""
        self._check_bounds(2)
        val = struct.unpack_from("<H", self._data, self._pos)[0]
        self._pos += 2
        return val

    def read_i16(self) -> int:
        """Read a signed 16-bit little-endian integer."""
        self._check_bounds(2)
        val = struct.unpack_from("<h", self._data, self._pos)[0]
        self._pos += 2
        return val

    def read_u32(self) -> int:
        """Read an unsigned 32-bit little-endian integer."""
        self._check_bounds(4)
        val = struct.unpack_from("<I", self._data, self._pos)[0]
        self._pos += 4
        return val

    def read_i32(self) -> int:
        """Read a signed 32-bit little-endian integer."""
        self._check_bounds(4)
        val = struct.unpack_from("<i", self._data, self._pos)[0]
        self._pos += 4
        return val

    def read_string(self, length: int, encoding: str = "ascii") -> str:
        """Read a fixed-length string, stripping null bytes."""
        raw = self.read_bytes(length)
        # Strip trailing nulls and whitespace
        return raw.split(b"\x00", 1)[0].decode(encoding, errors="replace").rstrip()

    def read_cstring(self, max_length: int = 256) -> str:
        """Read a null-terminated string up to max_length."""
        start = self._pos
        end = self._data.find(b"\x00", self._pos, self._pos + max_length)
        if end == -1:
            end = min(self._pos + max_length, len(self._data))
        result = self._data[start:end].decode("ascii", errors="replace")
        self._pos = end + 1  # skip past the null terminator
        return result

    def read_bool(self) -> bool:
        """Read a single byte as a boolean."""
        return self.read_u8() != 0

    def read_bitfield(self, num_bytes: int) -> list[bool]:
        """Read num_bytes and return a list of individual bit values (LSB first)."""
        raw = self.read_bytes(num_bytes)
        bits: list[bool] = []
        for byte in raw:
            for bit_index in range(8):
                bits.append(bool(byte & (1 << bit_index)))
        return bits

    def sub_reader(self, offset: int, length: int) -> BinaryReader:
        """Create a new BinaryReader for a sub-section of the data."""
        if offset + length > len(self._data):
            raise BinaryReaderError(
                f"Sub-reader range [0x{offset:X}, 0x{offset + length:X}) "
                f"exceeds buffer size 0x{len(self._data):X} in {self._name}"
            )
        return BinaryReader(
            self._data[offset : offset + length],
            name=f"{self._name}[0x{offset:X}:0x{offset + length:X}]",
        )

    def hex_dump(self, offset: int, length: int, columns: int = 16) -> str:
        """Return a hex dump string for debugging."""
        end = min(offset + length, len(self._data))
        lines: list[str] = []
        for i in range(offset, end, columns):
            chunk = self._data[i : min(i + columns, end)]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append(f"  {i:08X}  {hex_part:<{columns * 3}}  {ascii_part}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"BinaryReader({self._name}, pos=0x{self._pos:X}, "
            f"size=0x{len(self._data):X})"
        )


class BinaryWriter:
    """Writes binary data in little-endian format for save game output."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    @property
    def size(self) -> int:
        return len(self._buffer)

    def get_bytes(self) -> bytes:
        return bytes(self._buffer)

    def write_to_file(self, path: Path | str) -> None:
        Path(path).write_bytes(self._buffer)

    def write_u8(self, value: int) -> None:
        self._buffer.append(value & 0xFF)

    def write_i8(self, value: int) -> None:
        self._buffer.extend(struct.pack("<b", value))

    def write_u16(self, value: int) -> None:
        self._buffer.extend(struct.pack("<H", value))

    def write_i16(self, value: int) -> None:
        self._buffer.extend(struct.pack("<h", value))

    def write_u32(self, value: int) -> None:
        self._buffer.extend(struct.pack("<I", value))

    def write_i32(self, value: int) -> None:
        self._buffer.extend(struct.pack("<i", value))

    def write_bytes(self, data: bytes) -> None:
        self._buffer.extend(data)

    def write_string(self, text: str, length: int, encoding: str = "ascii") -> None:
        """Write a fixed-length string, padded with null bytes."""
        encoded = text.encode(encoding)[:length]
        self._buffer.extend(encoded)
        self._buffer.extend(b"\x00" * (length - len(encoded)))

    def write_bitfield(self, bits: list[bool]) -> None:
        """Write a list of booleans as packed bytes (LSB first)."""
        num_bytes = (len(bits) + 7) // 8
        for byte_idx in range(num_bytes):
            byte_val = 0
            for bit_idx in range(8):
                flat_idx = byte_idx * 8 + bit_idx
                if flat_idx < len(bits) and bits[flat_idx]:
                    byte_val |= 1 << bit_idx
            self._buffer.append(byte_val)
