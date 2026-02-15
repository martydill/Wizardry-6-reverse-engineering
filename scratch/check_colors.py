
import pygame
from pathlib import Path

def main():
    pygame.init()
    surf = pygame.image.load('perms/perm_0123.png')
    w, h = surf.get_size()
    counts = {}
    for y in range(h):
        for x in range(w):
            c = surf.get_at((x, y))
            rgb = (c.r, c.g, c.b)
            counts[rgb] = counts.get(rgb, 0) + 1
            
    sorted_counts = sorted(counts.items(), key=lambda t: t[1], reverse=True)
    for rgb, count in sorted_counts[:10]:
        print(f"{rgb}: {count}")

if __name__ == "__main__":
    main()
