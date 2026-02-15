import pygame
import sys
from pathlib import Path

# Constants
WIDTH, HEIGHT = 1000, 800
OFFSET_X, OFFSET_Y = 50, 100

# Colors
COLOR_BG = (30, 30, 35)
COLOR_GRID = (60, 60, 65)
COLOR_WALL = (255, 255, 255)
COLOR_CHANGED = (120, 60, 60)
COLOR_TEXT = (220, 220, 220)
COLOR_HOVER = (0, 255, 255)

class MultiMapViewer:
    def __init__(self, file_new, file_old):
        self.data_new = self.load_data(file_new)
        self.data_old = self.load_data(file_old)
        self.start_cell = 3167  # Start at the run of 16 walls
        self.grid_w = 16
        self.grid_h = 16
        self.cell_size = 30
        self.bpc = 8
        self.diff_cells = self.get_diff_cells()

    def load_data(self, path):
        if not Path(path).exists():
            return None
        return Path(path).read_bytes()

    def get_diff_cells(self):
        if self.data_new is None or self.data_old is None: return set()
        diffs = set()
        for i in range(min(len(self.data_new), len(self.data_old))):
            if self.data_new[i] != self.data_old[i]:
                diffs.add(i // self.bpc)
        return diffs

    def draw_cell(self, screen, map_cell_idx):
        global_cell_idx = self.start_cell + map_cell_idx
        
        row = map_cell_idx // self.grid_w
        col = map_cell_idx % self.grid_w
        
        x = OFFSET_X + col * self.cell_size
        y = OFFSET_Y + row * self.cell_size

        if x < 0 or x >= WIDTH - 250 or y < 0 or y >= HEIGHT - 50:
            return

        if global_cell_idx in self.diff_cells:
            pygame.draw.rect(screen, COLOR_CHANGED, (x, y, self.cell_size, self.cell_size))
        
        pygame.draw.rect(screen, COLOR_GRID, (x, y, self.cell_size, self.cell_size), 1)

        base = global_cell_idx * self.bpc
        if base + 7 < len(self.data_new):
            b3 = self.data_new[base + 3]
            b5 = self.data_new[base + 5]
            if b3 & 0x80: pygame.draw.line(screen, COLOR_WALL, (x, y), (x + self.cell_size, y), 2)
            if b3 & 0x40: pygame.draw.line(screen, COLOR_WALL, (x, y + self.cell_size), (x + self.cell_size, y + self.cell_size), 2)
            if b5 & 0x80: pygame.draw.line(screen, COLOR_WALL, (x, y), (x, y + self.cell_size), 2)
            if b5 & 0x20: pygame.draw.line(screen, (100, 255, 100), (x + self.cell_size, y), (x + self.cell_size, y + self.cell_size), 2)

    def run(self):
        pygame.init()
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Wizardry 6 - Map Explorer")
        font = pygame.font.SysFont("monospace", 16)
        clock = pygame.time.Clock()

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_n: self.start_cell += 16
                    if event.key == pygame.K_p: self.start_cell -= 16
                    if event.key == pygame.K_UP: self.grid_w += 1
                    if event.key == pygame.K_DOWN: self.grid_w = max(1, self.grid_w - 1)
                    if event.key == pygame.K_RIGHT: self.grid_w += 10
                    if event.key == pygame.K_LEFT: self.grid_w = max(1, self.grid_w - 10)
                    if event.key == pygame.K_PAGEUP: self.start_cell += self.grid_w * self.grid_h
                    if event.key == pygame.K_PAGEDOWN: self.start_cell -= self.grid_w * self.grid_h

            screen.fill(COLOR_BG)

            status = [
                f"START CELL: {self.start_cell}",
                f"OFFSET: 0x{self.start_cell * 8:04X}",
                f"WIDTH: {self.grid_w}",
                "",
                "ARROWS: Adj Width | N/P: Adj Offset | PGUP/DN: Page"
            ]
            for i, text in enumerate(status):
                img = font.render(text, True, COLOR_TEXT)
                screen.blit(img, (20, 10 + i * 18))

            for i in range(16 * 16): # Show 16x16 grid
                self.draw_cell(screen, i)

            pygame.display.flip()
            clock.tick(30)
        pygame.quit()

if __name__ == "__main__":
    viewer = MultiMapViewer("gamedata/NEWGAME.DBS", "gamedata/newgameoriginal.DBS")
    viewer.run()
