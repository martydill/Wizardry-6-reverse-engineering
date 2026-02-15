def dump_map(data, start_cell, w, h, column_major=True):
    lines = []
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
        lines.append(line)
    return lines

def search():
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()
    
    for m in range(16):
        start_cell = m * 400
        print("\n--- Map {} at cell {} ---".format(m, start_cell))
        for w in [16, 20, 24, 28, 32]:
            h = w
            print("Width {}:".format(w))
            lines = dump_map(data, start_cell, w, 5, column_major=True)
            for l in lines: print(l)

if __name__ == "__main__":
    search()
