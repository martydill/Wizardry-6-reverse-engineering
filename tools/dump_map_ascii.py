def dump_map(start_cell, w, h, column_major=True):
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()
    
    print(f"Map at cell {start_cell}, size {w}x{h}, {'Column' if column_major else 'Row'}-Major")
    
    for r in range(h):
        line = ""
        for c in range(w):
            if column_major:
                idx = start_cell + c * h + r
            else:
                idx = start_cell + r * w + c
            
            b3 = data[idx*8 + 3]
            b5 = data[idx*8 + 5]
            
            # Simple ASCII: # for cell, | for West wall, _ for North wall
            # Actually let's just use + for wall intersections
            char = "#"
            if b3 & 0x80: char = "N"
            if b5 & 0x80: char = "W"
            if (b3 & 0x80) and (b5 & 0x80): char = "+"
            line += char
        print(line)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: dump_map_ascii.py <start_cell> <w> <h> [col/row]")
        sys.exit(1)
    
    start = int(sys.argv[1])
    w = int(sys.argv[2])
    h = int(sys.argv[3])
    cm = True
    if len(sys.argv) > 4 and sys.argv[4].lower() == 'row':
        cm = False
    
    dump_map(start, w, h, column_major=cm)
