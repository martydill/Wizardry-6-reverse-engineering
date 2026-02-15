import struct

def find_metadata(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    
    print(f"File: {filepath} ({len(data)} bytes)")
    
    # Search for (16, 16) or (20, 20) or (28, 28)
    targets = [(16, 16), (20, 20), (28, 28), (32, 32)]
    for w, h in targets:
        pattern = struct.pack('<HH', w, h)
        idx = data.find(pattern)
        while idx != -1:
            print(f"Found {w}x{h} at offset 0x{idx:04X}")
            idx = data.find(pattern, idx + 1)

    # Search for possible offset table
    # If there are 16 maps, look for a sequence of 16 increasing words or longs
    for i in range(len(data) - 64):
        vals = struct.unpack('<16H', data[i:i+32])
        if all(vals[j] < vals[j+1] for j in range(len(vals)-1)) and vals[0] < 0x1000:
            print(f"Possible 16-word offset table at 0x{i:04X}: {vals}")

if __name__ == "__main__":
    find_metadata('gamedata/NEWGAME.DBS')
