import pygame
from pathlib import Path
from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE

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
    path = Path('gamedata/TITLEPAG.EGA')
    if not path.exists(): return
    data = path.read_bytes()
    
    decoder = EGADecoder()
    
    # Try different offsets and methods
    results = []
    for offset in [0, 768]:
        payload = data[offset:offset+32000]
        if len(payload) < 32000: continue
        
        # Method 1: Sequential Planar
        s_seq = decoder.decode_planar(payload, 320, 200)
        results.append((f"seq_off_{offset}_0123", score_sprite(s_seq)))
        
        s_seq2 = decoder.decode_planar(payload, 320, 200, plane_order=[3, 0, 2, 1])
        results.append((f"seq_off_{offset}_3021", score_sprite(s_seq2)))

        # Method 2: Row Interleaved
        s_row = decoder.decode_planar_row_interleaved(payload, 320, 200)
        results.append((f"row_off_{offset}_0123", score_sprite(s_row)))
        
        s_row2 = decoder.decode_planar_row_interleaved(payload, 320, 200, plane_order=[3, 0, 2, 1])
        results.append((f"row_off_{offset}_3021", score_sprite(s_row2)))
        
        # Method 3: Tiled Planar
        s_tile = decoder.decode_tiled_planar(payload, 320, 200)
        results.append((f"tile_off_{offset}", score_sprite(s_tile)))

    for name, score in sorted(results, key=lambda x: x[1], reverse=True):
        print(f"{name}: {score}")

test()
