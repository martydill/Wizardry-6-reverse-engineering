"""Tests for the BinaryReader and BinaryWriter."""

import struct

import pytest

from bane.data.binary_reader import BinaryReader, BinaryReaderError, BinaryWriter


class TestBinaryReader:
    def test_read_u8(self):
        reader = BinaryReader(bytes([0x00, 0x7F, 0xFF]))
        assert reader.read_u8() == 0
        assert reader.read_u8() == 127
        assert reader.read_u8() == 255

    def test_read_i8(self):
        reader = BinaryReader(bytes([0x00, 0x7F, 0x80, 0xFF]))
        assert reader.read_i8() == 0
        assert reader.read_i8() == 127
        assert reader.read_i8() == -128
        assert reader.read_i8() == -1

    def test_read_u16_little_endian(self):
        reader = BinaryReader(bytes([0x34, 0x12]))
        assert reader.read_u16() == 0x1234

    def test_read_i16_little_endian(self):
        reader = BinaryReader(bytes([0xFF, 0xFF]))
        assert reader.read_i16() == -1

    def test_read_u32_little_endian(self):
        reader = BinaryReader(bytes([0x78, 0x56, 0x34, 0x12]))
        assert reader.read_u32() == 0x12345678

    def test_read_string(self):
        data = b"Hello\x00\x00\x00\x00\x00"  # 10 bytes
        reader = BinaryReader(data)
        assert reader.read_string(10) == "Hello"

    def test_read_string_full(self):
        data = b"0123456789"
        reader = BinaryReader(data)
        assert reader.read_string(10) == "0123456789"

    def test_read_cstring(self):
        data = b"Hello\x00World\x00"
        reader = BinaryReader(data)
        assert reader.read_cstring() == "Hello"
        assert reader.read_cstring() == "World"

    def test_read_bool(self):
        reader = BinaryReader(bytes([0x00, 0x01, 0xFF]))
        assert reader.read_bool() is False
        assert reader.read_bool() is True
        assert reader.read_bool() is True

    def test_read_bitfield(self):
        reader = BinaryReader(bytes([0b10110001]))
        bits = reader.read_bitfield(1)
        assert bits == [True, False, False, False, True, True, False, True]

    def test_seek(self):
        reader = BinaryReader(bytes([0, 1, 2, 3, 4]))
        reader.seek(3)
        assert reader.read_u8() == 3

    def test_skip(self):
        reader = BinaryReader(bytes([0, 1, 2, 3, 4]))
        reader.skip(2)
        assert reader.read_u8() == 2

    def test_position_tracking(self):
        reader = BinaryReader(bytes(10))
        assert reader.position == 0
        reader.read_u8()
        assert reader.position == 1
        reader.read_u16()
        assert reader.position == 3
        reader.read_u32()
        assert reader.position == 7

    def test_size_and_remaining(self):
        reader = BinaryReader(bytes(10))
        assert reader.size == 10
        assert reader.remaining == 10
        reader.read_u32()
        assert reader.remaining == 6
        assert not reader.at_end

    def test_bounds_check(self):
        reader = BinaryReader(bytes([0]))
        reader.read_u8()
        with pytest.raises(BinaryReaderError):
            reader.read_u8()

    def test_seek_out_of_bounds(self):
        reader = BinaryReader(bytes(5))
        with pytest.raises(BinaryReaderError):
            reader.seek(10)

    def test_sub_reader(self):
        reader = BinaryReader(bytes([0, 1, 2, 3, 4, 5, 6, 7]))
        sub = reader.sub_reader(2, 4)
        assert sub.size == 4
        assert sub.read_u8() == 2
        assert sub.read_u8() == 3

    def test_peek_bytes(self):
        reader = BinaryReader(bytes([0xAA, 0xBB, 0xCC]))
        peeked = reader.peek_bytes(2)
        assert peeked == bytes([0xAA, 0xBB])
        # Position should not advance
        assert reader.position == 0

    def test_hex_dump(self):
        reader = BinaryReader(bytes(range(32)))
        dump = reader.hex_dump(0, 16)
        assert "00000000" in dump
        assert "0F" in dump


class TestBinaryWriter:
    def test_write_u8(self):
        w = BinaryWriter()
        w.write_u8(0xFF)
        assert w.get_bytes() == bytes([0xFF])

    def test_write_u16(self):
        w = BinaryWriter()
        w.write_u16(0x1234)
        assert w.get_bytes() == bytes([0x34, 0x12])

    def test_write_u32(self):
        w = BinaryWriter()
        w.write_u32(0x12345678)
        assert w.get_bytes() == bytes([0x78, 0x56, 0x34, 0x12])

    def test_write_string(self):
        w = BinaryWriter()
        w.write_string("Hi", 5)
        assert w.get_bytes() == b"Hi\x00\x00\x00"

    def test_write_string_truncated(self):
        w = BinaryWriter()
        w.write_string("Hello World", 5)
        assert w.get_bytes() == b"Hello"

    def test_write_bitfield(self):
        w = BinaryWriter()
        w.write_bitfield([True, False, False, False, True, True, False, True])
        assert w.get_bytes() == bytes([0b10110001])

    def test_roundtrip(self):
        """Write data and read it back."""
        w = BinaryWriter()
        w.write_u8(42)
        w.write_u16(1000)
        w.write_u32(999999)
        w.write_string("Test", 10)

        r = BinaryReader(w.get_bytes())
        assert r.read_u8() == 42
        assert r.read_u16() == 1000
        assert r.read_u32() == 999999
        assert r.read_string(10) == "Test"
