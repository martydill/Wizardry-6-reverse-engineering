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
        print(f"Found {sig_hex[:20]}... in {filename} at {pos} (0x{pos:04X})")
        pos += 1

sig10 = '88 00 8a 00 8a 00 02 20 aa 2a 80 22 a8 2a 08 28 aa aa 00 00'
find_signatures('gamedata/SCENARIO.DBS', sig10)
find_signatures('gamedata/NEWGAME.DBS', sig10)
