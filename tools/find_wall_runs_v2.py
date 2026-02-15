def find_runs():
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()
    
    num_cells = len(data) // 8
    
    print("Searching for West wall runs (16, 20, 28)...")
    
    for length in [16, 20, 28]:
        for i in range(num_cells - length):
            # West wall run (B5 & 0x80)
            if all(data[(i+j*length)*8 + 5] & 0x80 for j in range(length)):
                 # This would be a column of west walls if we assume width = length
                 pass

    # Actually, let's just look for any run of N walls in a row in the file
    for length in [16, 20, 28]:
        for i in range(num_cells - length):
            if all(data[(i+j)*8 + 5] & 0x80 for j in range(length)):
                print(f"Length {length} West wall run at cell {i} (offset 0x{i*8:04X})")

if __name__ == "__main__":
    find_runs()
