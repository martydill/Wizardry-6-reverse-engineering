"""Tests for the EGA sprite decoder."""

from bane.data.sprite_decoder import (
    DEFAULT_16_PALETTE,
    EGA_64_PALETTE,
    EGADecoder,
    Sprite,
    SpriteAtlas,
)


class TestEGAPalette:
    def test_64_palette_size(self):
        assert len(EGA_64_PALETTE) == 64

    def test_black_is_first(self):
        assert EGA_64_PALETTE[0] == (0, 0, 0)

    def test_white_is_last(self):
        assert EGA_64_PALETTE[63] == (255, 255, 255)

    def test_16_palette_size(self):
        assert len(DEFAULT_16_PALETTE) == 16

    def test_16_palette_black_and_white(self):
        assert DEFAULT_16_PALETTE[0] == (0, 0, 0)  # black
        assert DEFAULT_16_PALETTE[15] == (255, 255, 255)  # white

    def test_all_colors_valid_rgb(self):
        for r, g, b in EGA_64_PALETTE:
            assert 0 <= r <= 255
            assert 0 <= g <= 255
            assert 0 <= b <= 255


class TestSprite:
    def test_basic_sprite(self):
        sprite = Sprite(width=4, height=2, pixels=[0] * 8, palette=list(DEFAULT_16_PALETTE))
        assert sprite.pixel_count == 8

    def test_get_pixel(self):
        sprite = Sprite(width=2, height=2, pixels=[0, 1, 2, 3], palette=list(DEFAULT_16_PALETTE))
        assert sprite.get_pixel(0, 0) == 0
        assert sprite.get_pixel(1, 0) == 1
        assert sprite.get_pixel(0, 1) == 2
        assert sprite.get_pixel(1, 1) == 3

    def test_get_pixel_out_of_bounds(self):
        sprite = Sprite(width=2, height=2, pixels=[5, 5, 5, 5], palette=list(DEFAULT_16_PALETTE))
        assert sprite.get_pixel(-1, 0) == 0
        assert sprite.get_pixel(0, 10) == 0

    def test_get_rgb(self):
        sprite = Sprite(width=1, height=1, pixels=[0], palette=list(DEFAULT_16_PALETTE))
        assert sprite.get_rgb(0, 0) == (0, 0, 0)  # black

    def test_to_rgba_bytes(self):
        sprite = Sprite(
            width=2, height=1,
            pixels=[0, 15],
            palette=list(DEFAULT_16_PALETTE),
        )
        rgba = sprite.to_rgba_bytes()
        assert len(rgba) == 8  # 2 pixels * 4 bytes
        # First pixel: black with full alpha
        assert rgba[0] == 0 and rgba[1] == 0 and rgba[2] == 0 and rgba[3] == 255
        # Second pixel: white with full alpha
        assert rgba[4] == 255 and rgba[5] == 255 and rgba[6] == 255 and rgba[7] == 255

    def test_to_rgba_transparent(self):
        sprite = Sprite(
            width=1, height=1,
            pixels=[5],
            palette=list(DEFAULT_16_PALETTE),
        )
        rgba = sprite.to_rgba_bytes(transparent_index=5)
        assert rgba == b"\x00\x00\x00\x00"

    def test_scale(self):
        sprite = Sprite(width=2, height=2, pixels=[0, 1, 2, 3], palette=list(DEFAULT_16_PALETTE))
        scaled = sprite.scale(2)
        assert scaled.width == 4
        assert scaled.height == 4
        assert scaled.get_pixel(0, 0) == 0
        assert scaled.get_pixel(1, 0) == 0
        assert scaled.get_pixel(2, 0) == 1
        assert scaled.get_pixel(3, 0) == 1
        assert scaled.get_pixel(0, 2) == 2


class TestEGADecoder:
    def test_decode_planar_all_black(self):
        decoder = EGADecoder()
        # 8x1 image, all black (all planes zero)
        data = bytes(4)  # 4 planes × 1 byte each
        sprite = decoder.decode_planar(data, 8, 1)
        assert sprite.width == 8
        assert sprite.height == 1
        assert all(p == 0 for p in sprite.pixels)

    def test_decode_planar_all_white(self):
        decoder = EGADecoder()
        # 8x1 image, all planes set = color 15
        data = bytes([0xFF, 0xFF, 0xFF, 0xFF])
        sprite = decoder.decode_planar(data, 8, 1)
        assert all(p == 15 for p in sprite.pixels)

    def test_decode_planar_plane0_only(self):
        decoder = EGADecoder()
        # 8x1, only plane 0 set = color 1
        data = bytes([0xFF, 0x00, 0x00, 0x00])
        sprite = decoder.decode_planar(data, 8, 1)
        assert all(p == 1 for p in sprite.pixels)

    def test_decode_linear(self):
        decoder = EGADecoder()
        # 4x1 image: colors 0, 1, 2, 3 packed as nibbles
        data = bytes([0x01, 0x23])
        sprite = decoder.decode_linear(data, 4, 1)
        assert sprite.pixels == [0, 1, 2, 3]

    def test_decode_byte_per_pixel(self):
        decoder = EGADecoder()
        data = bytes([5, 10, 0, 15])
        sprite = decoder.decode_byte_per_pixel(data, 2, 2)
        assert sprite.pixels == [5, 10, 0, 15]

    def test_custom_palette(self):
        custom = [(i * 16, i * 16, i * 16) for i in range(16)]
        decoder = EGADecoder(palette=custom)
        data = bytes(4)
        sprite = decoder.decode_planar(data, 8, 1)
        assert sprite.palette == custom

    def test_set_palette_from_registers(self):
        decoder = EGADecoder()
        registers = [0, 63, 7, 56] + [0] * 12
        decoder.set_palette_from_ega_registers(registers)
        assert decoder.palette[0] == (0, 0, 0)  # register 0 -> black
        assert decoder.palette[1] == (255, 255, 255)  # register 63 -> white


class TestSpriteAtlas:
    def test_add_and_get(self):
        atlas = SpriteAtlas()
        sprite = Sprite(width=8, height=8, pixels=[0] * 64, palette=list(DEFAULT_16_PALETTE))
        atlas.add_sprite(42, sprite)
        assert 42 in atlas
        assert atlas.get_sprite(42) is sprite
        assert atlas.count == 1

    def test_missing_sprite(self):
        atlas = SpriteAtlas()
        assert atlas.get_sprite(999) is None
        assert 999 not in atlas

    def test_sprite_ids(self):
        atlas = SpriteAtlas()
        for i in [5, 1, 10, 3]:
            atlas.add_sprite(i, Sprite(width=1, height=1, pixels=[0], palette=[]))
        assert atlas.sprite_ids == [1, 3, 5, 10]
