
import pygame
import os
from pathlib import Path

def score_image(path):
    surf = pygame.image.load(path)
    w, h = surf.get_size()
    red_count = 0
    yellow_count = 0
    brown_count = 0
    
    # Color 4: (170, 0, 0) - Red
    # Color 14: (255, 255, 85) - Yellow
    # Color 6: (170, 85, 0) - Brown
    
    for y in range(h):
        for x in range(w):
            r, g, b, a = surf.get_at((x, y))
            if r == 170 and g == 0 and b == 0:
                red_count += 1
            elif r == 255 and g == 255 and b == 85:
                yellow_count += 1
            elif r == 170 and g == 85 and b == 0:
                brown_count += 1
                
    return red_count, yellow_count, brown_count

def main():
    pygame.init()
    results = []
    for p in Path('perms').glob('*.png'):
        r, y, b = score_image(p)
        results.append((p.name, r, y, b))
        
    # Sort by Red + Yellow + Brown
    results.sort(key=lambda t: t[1] + t[2] + t[3], reverse=True)
    for name, r, y, b in results[:10]:
        print(f"{name}: Red={r:6}, Yellow={y:6}, Brown={b:6} Total={r+y+b}")

if __name__ == "__main__":
    main()
