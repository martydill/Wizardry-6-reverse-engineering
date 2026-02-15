def search():
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()
    
    print(f"Searching for 16-entry dimension tables...")
    
    valid_dims = {16, 20, 28, 32}
    
    for i in range(len(data) - 16):
        chunk = data[i:i+16]
        if all(b in valid_dims for b in chunk):
            print(f"Possible 16-byte dim table at 0x{i:04X}: {chunk.hex(' ')}")
            
    # Also look for 16-word tables
    for i in range(len(data) - 32):
        chunk = data[i:i+32]
        import struct
        words = struct.unpack('<16H', chunk)
        if all(w in valid_dims for w in words):
            print(f"Possible 16-word dim table at 0x{i:04X}: {words}")

if __name__ == "__main__":
    search()
