import sys

def find_signatures(filename, sig_hex):
    sig = bytes.fromhex(sig_hex)
    with open(filename, 'rb') as f:
        data = f.read()
    
    pos = 0
    while True:
        pos = data.find(sig, pos)
        if pos == -1:
            break
        print(f"Found at {pos} (0x{pos:04X})")
        pos += 1

sig1 = '00 00 00 00 00 00 02 00 02 06 00 00 b4 00 00 00 00 00 00 00'
print(f"Searching for Map 1 signature {sig1}...")
find_signatures('gamedata/NEWGAME.DBS', sig1)
