from bane.data.pic_decoder import _decode_rle
from bane.data.sprite_decoder import EGADecoder
from pathlib import Path

def score_sprite(sprite):
    pixels = sprite.pixels
    w = sprite.width
    h = sprite.height
    score = 0
    for y in range(h):
        row = pixels[y*w : (y+1)*w]
        for x in range(1, w):
            if row[x] == row[x-1]: score += 1
    for x in range(w):
        for y in range(1, h):
            if pixels[y*w+x] == pixels[(y-1)*w+x]: score += 1
    return score

def test():
    path = Path('gamedata/credits.pic')
    if not path.exists(): return
    data = path.read_bytes()
    decompressed = _decode_rle(data)
    
    # credits.pic is likely full-screen if it's the credits
    # But wait, it might have a frame header.
    # Let's try offset 600 (0x258) which is standard PIC header.
    offset = 600
    payload = decompressed[offset:offset+32000]
    if len(payload) < 32000:
        print(f"Payload too small: {len(payload)}")
        return
    
    decoder = EGADecoder()
    results = []
    w, h = 320, 200
    
    s_seq = decoder.decode_planar(payload, w, h)
    results.append(("seq", score_sprite(s_seq)))
    
    s_row = decoder.decode_planar_row_interleaved(payload, w, h)
    results.append(("row", score_sprite(s_row)))
    
    s_tile = decoder.decode_tiled_planar(payload, w, h)
    results.append(("tile", score_sprite(s_tile)))

    for name, score in sorted(results, key=lambda x: x[1], reverse=True):
        print(f"{name}: {score}")

test()
