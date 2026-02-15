
import pygame
import os
from pathlib import Path
from bane.data.sprite_decoder import EGADecoder, Sprite

def load_titlepag(path_str):
    path = Path(path_str)
    data = path.read_bytes()
    
    # Header is 768 bytes
    # It seems to contain a 256-color palette (768 bytes)
    # But we only need the first 16 colors for 4bpp
    pal_data = data[:768]
    palette = []
    for i in range(16):
        r = pal_data[i*3]
        g = pal_data[i*3+1]
        b = pal_data[i*3+2]
        palette.append((r, g, b))
    
    decoder = EGADecoder(palette=palette)
    # The image data starts at 768 and is 320x200 row-interleaved planar
    sprite = decoder.decode_planar_row_interleaved(data[768:], 320, 200)
    return sprite

if __name__ == "__main__":
    pygame.init()
    os.makedirs('output', exist_ok=True)
    
    for name in ['TITLEPAG.EGA', 'DRAGONSC.EGA', 'GRAVEYRD.EGA']:
        path = f'gamedata/{name}'
        if not os.path.exists(path):
            continue
        sprite = load_titlepag(path)
        print(f"Loaded {name}: {sprite.width}x{sprite.height}")
        
        rgba = sprite.to_rgba_bytes()
        surf = pygame.image.frombuffer(rgba, (320, 200), "RGBA")
        pygame.image.save(surf, f"output/{name.lower()}.png")
        print(f"Saved output/{name.lower()}.png")
    
    pygame.quit()
