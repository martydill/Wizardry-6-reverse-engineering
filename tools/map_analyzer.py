import sys

def get_map_info(index):
    # Hypothesis: Maps 0-9 are 20x20, Map 10 is 16x16, Maps 11-15 are 20x20
    w = 20
    h = 20
    if index == 10:
        w, h = 16, 16
    
    # Calculate start cell
    start_cell = 0
    for i in range(index):
        if i == 10:
            start_cell += 16 * 16
        else:
            start_cell += 20 * 20
    
    return start_cell, w, h

def dump_map(filename, index):
    with open(filename, 'rb') as f:
        data = f.read()
    
    start_cell, w, h = get_map_info(index)
    print(f"Map {index} at cell {start_cell} (offset 0x{start_cell*8:04X}), size {w}x{h}")
    
    for r in range(h):
        line = ""
        for c in range(w):
            idx = start_cell + c * h + r
            if idx * 8 + 7 >= len(data):
                line += "?"
                continue
            
            b3 = data[idx*8 + 3]
            b5 = data[idx*8 + 5]
            
            char = "."
            if b3 & 0x80: char = "N"
            if b5 & 0x80: char = "W"
            if (b3 & 0x80) and (b5 & 0x80): char = "+"
            line += char
        print(line)

if __name__ == "__main__":
    file = "gamedata/NEWGAME.DBS"
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    dump_map(file, idx)
