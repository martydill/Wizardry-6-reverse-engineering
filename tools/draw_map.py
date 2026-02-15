import sys

def draw_map(filename):
    with open(filename, 'rb') as f:
        data = f.read()
    
    # 20x20 grid
    for r in range(20):
        # North walls
        line = ""
        for c in range(20):
            cell_idx = r * 20 + c
            b3 = data[cell_idx * 8 + 3] if cell_idx * 8 + 3 < len(data) else 0
            if b3 & 0x80:
                line += "+---"
            else:
                line += "+   "
        print(line + "+")
        
        # West/East walls
        line = ""
        for c in range(20):
            cell_idx = r * 20 + c
            b5 = data[cell_idx * 8 + 5] if cell_idx * 8 + 5 < len(data) else 0
            if b5 & 0x20:
                line += "|   "
            else:
                line += "    "
        # Final east wall
        cell_idx = r * 20 + 19
        b5 = data[cell_idx * 8 + 5] if cell_idx * 8 + 5 < len(data) else 0
        if b5 & 0x80:
            line += "|"
        else:
            line += " "
        print(line)
    
    # Bottom edge
    line = ""
    for c in range(20):
        cell_idx = 19 * 20 + c
        b3 = data[cell_idx * 8 + 3] if cell_idx * 8 + 3 < len(data) else 0
        if b3 & 0x40:
            line += "+---"
        else:
            line += "+   "
    print(line + "+")

if __name__ == "__main__":
    draw_map(sys.argv[1])
