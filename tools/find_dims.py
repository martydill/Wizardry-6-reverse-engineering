import sys

def find_dims(filename, w, h):
    targets = [
        bytes([w, h]),
        bytes([w, 0, h, 0]),
        bytes([h, w]),
        bytes([h, 0, w, 0])
    ]
    with open(filename, 'rb') as f:
        data = f.read()
    
    for t in targets:
        pos = 0
        while True:
            pos = data.find(t, pos)
            if pos == -1:
                break
            print(f"Found {t.hex(' ')} at {pos} (0x{pos:04X})")
            pos += 1

print("Searching for 16x16 (10 10 or 10 00 10 00)...")
find_dims('gamedata/NEWGAME.DBS', 16, 16)
print("\nSearching for 20x20 (14 14 or 14 00 14 00)...")
find_dims('gamedata/NEWGAME.DBS', 20, 20)
print("\nSearching for 32x20 (20 14 or 20 00 14 00)...")
find_dims('gamedata/NEWGAME.DBS', 32, 20)
