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
        print(f"Found {sig_hex} in {filename} at {pos} (0x{pos:04X})")
        pos += 1

find_signatures('gamedata/SCENARIO.DBS', '88 00 8a 00 8a 00')
