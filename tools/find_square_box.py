def search():
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()
    
    num_cells = len(data) // 8
    
    for size in [16, 20]:
        print(f"Searching for {size}x{size} box...")
        for i in range(num_cells - size*size):
            # Check Column-Major Box
            # Top row (North): i, i+size, i+2*size ...
            north_walls = sum(1 for c in range(size) if data[(i + c*size)*8 + 3] & 0x80)
            # Left column (West): i, i+1, i+2 ...
            west_walls = sum(1 for r in range(size) if data[(i + r)*8 + 5] & 0x80)
            
            if north_walls > size * 0.8 and west_walls > size * 0.8:
                print(f"Potential {size}x{size} Col-Major box at cell {i} (offset 0x{i*8:04X})")
                print(f"  North: {north_walls}/{size}, West: {west_walls}/{size}")

            # Check Row-Major Box
            # Top row (North): i, i+1, i+2 ...
            north_walls = sum(1 for c in range(size) if data[(i + c)*8 + 3] & 0x80)
            # Left column (West): i, i+size, i+2*size ...
            west_walls = sum(1 for r in range(size) if data[(i + r*size)*8 + 5] & 0x80)
            
            if north_walls > size * 0.8 and west_walls > size * 0.8:
                print(f"Potential {size}x{size} Row-Major box at cell {i} (offset 0x{i*8:04X})")
                print(f"  North: {north_walls}/{size}, West: {west_walls}/{size}")

if __name__ == "__main__":
    search()
