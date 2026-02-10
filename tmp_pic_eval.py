import struct
from pathlib import Path
from bane.data.pic_decoder import _decode_rle
from bane.data.sprite_decoder import EGADecoder


def decode_linear_packed(payload, width, height):
    dec = EGADecoder()
    return dec.decode_linear(payload, width, height)


def decode_planar(payload, width, height, msb_first=True):
    dec = EGADecoder()
    return dec.decode_planar(payload, width, height, planes=4, msb_first=msb_first)


def decode_planar_row(payload, width, height, msb_first=True):
    dec = EGADecoder()
    return dec.decode_planar_row_interleaved(payload, width, height, planes=4, msb_first=msb_first)


def decode_tiled_planar(payload, width, height, msb_first=True):
    pixels = [0] * (width * height)
    pixel_idx = 0
    i = 0
    while i < len(payload) and pixel_idx < len(pixels):
        for byte_in_tile in range(8):
            if i + byte_in_tile >= len(payload):
                break
            for bit in range(8):
                if pixel_idx >= len(pixels):
                    break
                read_mask = (0x80 >> bit) if msb_first else (1 << bit)
                color = 0
                if i + byte_in_tile < len(payload) and payload[i + byte_in_tile] & read_mask:
                    color |= 0x01
                if i + byte_in_tile + 8 < len(payload) and payload[i + byte_in_tile + 8] & read_mask:
                    color |= 0x02
                if i + byte_in_tile + 16 < len(payload) and payload[i + byte_in_tile + 16] & read_mask:
                    color |= 0x04
                if i + byte_in_tile + 24 < len(payload) and payload[i + byte_in_tile + 24] & read_mask:
                    color |= 0x08
                pixels[pixel_idx] = color
                pixel_idx += 1
        i += 32
    return pixels


def score(pixels, width, height):
    s = 0
    for y in range(height):
        row = pixels[y*width:(y+1)*width]
        for x in range(1, width):
            if row[x] == row[x-1]:
                s += 1
    for x in range(width):
        prev = pixels[x]
        for y in range(1, height):
            v = pixels[y*width + x]
            if v == prev:
                s += 1
            prev = v
    return s


def best_for(path, width, height):
    raw = Path(path).read_bytes()
    comp = _decode_rle(raw)
    header = struct.unpack('<H', comp[:2])[0]
    payload = comp[header:]
    candidates = []
    spr = decode_linear_packed(payload, width, height)
    candidates.append(('linear_packed', score(spr.pixels, width, height)))
    spr = decode_planar(payload, width, height, True)
    candidates.append(('planar_msb', score(spr.pixels, width, height)))
    spr = decode_planar(payload, width, height, False)
    candidates.append(('planar_lsb', score(spr.pixels, width, height)))
    spr = decode_planar_row(payload, width, height, True)
    candidates.append(('planar_row_msb', score(spr.pixels, width, height)))
    spr = decode_planar_row(payload, width, height, False)
    candidates.append(('planar_row_lsb', score(spr.pixels, width, height)))
    pix = decode_tiled_planar(payload, width, height, True)
    candidates.append(('tiled_planar_msb', score(pix, width, height)))
    pix = decode_tiled_planar(payload, width, height, False)
    candidates.append(('tiled_planar_lsb', score(pix, width, height)))
    return sorted(candidates, key=lambda t: t[1], reverse=True)

for name in ['MON00.PIC','MON01.PIC','MON02.PIC','MON03.PIC','MON09.PIC']:
    path = 'gamedata/' + name
    # auto size by payload for 48x68 or 64x51
    import struct
    raw = Path(path).read_bytes()
    comp = _decode_rle(raw)
    header = struct.unpack('<H', comp[:2])[0]
    payload = comp[header:]
    size = len(payload)*2
    if size == 48*68:
        w,h = 48,68
    elif size == 64*51:
        w,h = 64,51
    else:
        w,h = 64,51
    best = best_for(path, w, h)
    print(name, w, h, best[:3])
