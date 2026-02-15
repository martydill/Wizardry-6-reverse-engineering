def find_runs():
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()
    
    num_cells = len(data) // 8
    
    print("Searching for wall runs of length 24...")
    
    for i in range(num_cells - 24):
        # North wall run (B3 & 0x80)
        if all(data[(i+j)*8 + 3] & 0x80 for j in range(24)):
            print(f"Length 24 North wall run at cell {i} (offset 0x{i*8:04X})")
        
        # West wall run (B5 & 0x80)
        if all(data[(i+j)*8 + 5] & 0x80 for j in range(24)):
            print(f"Length 24 West wall run at cell {i} (offset 0x{i*8:04X})")

if __name__ == "__main__":
    find_runs()
