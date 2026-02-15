import pygame
import sys
from pathlib import Path

# Constants
CELL_SIZE = 25
WIDTH, HEIGHT = 800, 600
OFFSET_X, OFFSET_Y = 50, 50

# Colors
COLOR_BG = (30, 30, 30)
COLOR_GRID = (60, 60, 60)
COLOR_WALL = (255, 255, 255)

def draw_map(screen, data, start_offset, w, h, title, font):
    screen.fill(COLOR_BG)
    txt = font.render(title, True, (200, 200, 200))
    screen.blit(txt, (20, 10))
    
    for r in range(h):
        for c in range(w):
            cell_idx = r * w + c
            base = start_offset + cell_idx * 8
            if base + 7 >= len(data): continue
            
            x = OFFSET_X + c * CELL_SIZE
            y = OFFSET_Y + r * CELL_SIZE
            
            pygame.draw.rect(screen, COLOR_GRID, (x, y, CELL_SIZE, CELL_SIZE), 1)
            
            b3 = data[base+3]
            b5 = data[base+5]
            
            if b3 & 0x80: pygame.draw.line(screen, COLOR_WALL, (x, y), (x+CELL_SIZE, y), 2)
            if b3 & 0x40: pygame.draw.line(screen, COLOR_WALL, (x, y+CELL_SIZE), (x+CELL_SIZE, y+CELL_SIZE), 2)
            if b5 & 0x80: pygame.draw.line(screen, COLOR_WALL, (x, y), (x, y+CELL_SIZE), 2)
            if b5 & 0x20: pygame.draw.line(screen, (100, 255, 100), (x+CELL_SIZE, y), (x+CELL_SIZE, y+CELL_SIZE), 2)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    font = pygame.font.SysFont("monospace", 16)
    
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()
    
    # Map 10 start if everything was 20x20
    map10_20x20_start = 10 * 20 * 20 * 8 # 32000 = 0x7D00
    
    # Let's also look for Map 10 around where Map 9 might end if maps are variable
    # This is harder without a table. 
    # But if Map 10 is 16x16, let's see if 0x7D00 looks like a 16x16 map.
    
    modes = [
        (map10_20x20_start, 16, 16, "Map 10 as 16x16 (starting at 0x7D00)"),
        (map10_20x20_start, 20, 20, "Map 10 as 20x20 (starting at 0x7D00)")
    ]
    mode_idx = 0
    
    clock = pygame.time.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE: mode_idx = (mode_idx + 1) % len(modes)
        
        offset, w, h, title = modes[mode_idx]
        draw_map(screen, data, offset, w, h, title + " [SPACE to toggle]", font)
        
        pygame.display.flip()
        clock.tick(30)
    pygame.quit()

if __name__ == "__main__":
    main()
