import sys

def find_signatures(filename, sig_bytes):
    with open(filename, 'rb') as f:
        data = f.read()
    
    pos = 0
    while True:
        pos = data.find(sig_bytes, pos)
        if pos == -1:
            break
        print(f"Found {sig_bytes[:10].hex(' ')}... in {filename} at {pos} (0x{pos:04X})")
        pos += 1

with open('gamedata/NEWGAME.DBS', 'rb') as f:
    f.seek(0xA000)
    sig_at_a000 = f.read(20)

print(f"Signature at 0xA000 in NEWGAME.DBS: {sig_at_a000.hex(' ')}")
find_signatures('gamedata/SCENARIO.DBS', sig_at_a000)
find_signatures('gamedata/NEWGAME.DBS', sig_at_a000)
