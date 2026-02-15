def search():
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()
    
    size = len(data)
    print(f"File size: {size}")
    
    import struct
    
    # Search for potential offset tables
    # Most maps should be at 8-byte boundaries
    
    for i in range(0, 1024, 2): # Check first 1024 bytes
        chunk = data[i:i+32]
        if len(chunk) < 32: break
        
        words = struct.unpack('<16H', chunk)
        # See if these look like increasing offsets
        is_increasing = all(words[j] < words[j+1] for j in range(len(words)-1) if words[j+1] != 0)
        if is_increasing and words[0] > 0 and words[0] < size:
             print(f"Increasing word table at 0x{i:04X}: {words}")

        dwords = struct.unpack('<8I', chunk)
        is_increasing = all(dwords[j] < dwords[j+1] for j in range(len(dwords)-1) if dwords[j+1] != 0)
        if is_increasing and dwords[0] > 0 and dwords[0] < size:
             print(f"Increasing dword table at 0x{i:04X}: {dwords}")

if __name__ == "__main__":
    search()
