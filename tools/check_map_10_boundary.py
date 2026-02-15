def check():
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()
    
    start_cell = 3167
    w = 16
    h = 16
    
    # Column-Major: Index = start_cell + (col * h) + row
    
    # Top row (Row 0) North walls (B3 & 0x80)
    n_walls = [1 if data[(start_cell + c*h + 0)*8 + 3] & 0x80 else 0 for c in range(w)]
    print(f"Top row (Row 0) North: {n_walls}")
    
    # Bottom row (Row 15) South walls (B3 & 0x40)
    s_walls = [1 if data[(start_cell + c*h + 15)*8 + 3] & 0x40 else 0 for c in range(w)]
    print(f"Bottom row (Row 15) South: {s_walls}")
    
    # Left column (Col 0) West walls (B5 & 0x80)
    l_walls = [1 if data[(start_cell + 0*h + r)*8 + 5] & 0x80 else 0 for r in range(h)]
    print(f"Left col (Col 0) West: {l_walls}")
    
    # Right column (Col 15) East walls (B5 & 0x20 - assuming 0x20 is East)
    r_walls = [1 if data[(start_cell + 15*h + r)*8 + 5] & 0x20 else 0 for r in range(h)]
    print(f"Right col (Col 15) East: {r_walls}")

if __name__ == "__main__":
    check()
