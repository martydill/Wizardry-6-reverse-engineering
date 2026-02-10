
from pathlib import Path

def main():
    data = Path('gamedata/TITLEPAG.EGA').read_bytes()
    pal = data[:768]
    for i in range(16):
        r, g, b = pal[i*3 : i*3+3]
        print(f"Color {i:2}: ({r:3}, {g:3}, {b:3})")

if __name__ == "__main__":
    main()
