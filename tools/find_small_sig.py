import sys

def find_signatures(filename, sig_bytes):
    with open(filename, 'rb') as f:
        data = f.read()
    
    pos = 0
    while True:
        pos = data.find(sig_bytes, pos)
        if pos == -1:
            break
        print(f"Found {sig_bytes.hex(' ')} in {filename} at {pos} (0x{pos:04X})")
        pos += 1

with open('gamedata/NEWGAME.DBS', 'rb') as f:
    f.seek(14)
    sig8 = f.read(8)

print(f"Searching for {sig8.hex(' ')}...")
find_signatures('gamedata/SCENARIO.DBS', sig8)
find_signatures('gamedata/NEWGAME.DBS', sig8)
