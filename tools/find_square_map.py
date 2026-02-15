def search():
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()
    
    num_cells = len(data) // 8
    
    print("Searching for 16x16 square boundary (Column-Major)...")
    
    for i in range(num_cells - 256):
        # Check Col 0 West walls (assuming B5 & 0x80)
        # OR Col 0 North walls (assuming B3 & 0x80)
        
        # Test 1: Col 0 has 16 West walls
        col0_west = all(data[(i+r)*8 + 5] & 0x80 for r in range(16))
        if col0_west:
            # Check Row 0 North walls
            row0_north = all(data[(i+c*16)*8 + 3] & 0x80 for c in range(16))
            if row0_north:
                print(f"Possible 16x16 square at cell {i} (offset 0x{i*8:04X})")

if __name__ == "__main__":
    search()
