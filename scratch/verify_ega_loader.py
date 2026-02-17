import pygame
from pathlib import Path
from bane.data.sprite_decoder import decode_ega_file

def test():
    path = Path('gamedata/TITLEPAG.EGA')
    if not path.exists():
        print("File not found")
        return
    
    pygame.display.init()
    try:
        sprite = decode_ega_file(path)
        print(f"Decoded {path.name}: {sprite.width}x{sprite.height}")
        rgba = sprite.to_rgba_bytes()
        surf = pygame.image.frombuffer(rgba, (sprite.width, sprite.height), "RGBA")
        pygame.image.save(surf, "scratch/verify_title_seq.png")
        print("Saved scratch/verify_title_seq.png")
    except Exception as e:
        print(f"Error: {e}")
    pygame.quit()

test()
