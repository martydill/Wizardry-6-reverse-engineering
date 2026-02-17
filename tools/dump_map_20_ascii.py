import sys

def dump_map_20(filepath, offset, width, height, col_major=True):
    with open(filepath, 'rb') as f:
        f.seek(offset)
        data = f.read(width * height * 20)
    
    # Simple ASCII rendering for 20-byte cells
    # Use West bit (Bit 5) and East bit (Bit 7) in odd bytes
    
    # First, collect all walls
    # wall_map[row][col] = {W: bool, E: bool}
    wall_map = [[{'W': False, 'E': False} for _ in range(width)] for _ in range(height)]
    
    for cell_idx in range(width * height):
        if col_major:
            c = cell_idx // height
            r = cell_idx % height
        else:
            r = cell_idx // width
            c = cell_idx % width
        
        cell = data[cell_idx*20 : (cell_idx+1)*20]
        if not cell: break
        
        for byte_idx in range(1, 20, 2):
            byte_val = cell[byte_idx]
            base_row = (byte_idx - 1) // 2 * 2
            
            if byte_val & 0x20: # West
                for row_offset in range(2):
                    row = base_row + row_offset
                    if row < height:
                        wall_map[row][c]['W'] = True
            
            if byte_val & 0x80: # East
                for row_offset in range(2):
                    row = base_row + row_offset
                    if row < height:
                        wall_map[row][c]['E'] = True

    print(f"Map at 0x{offset:X}, size {width}x{height}, {'Column' if col_major else 'Row'}-Major (20-byte cells)")
    for r in range(height):
        line = ""
        for c in range(width):
            w = wall_map[r][c]['W']
            e = wall_map[r][c]['E']
            if w and e: char = "+"
            elif w: char = "W"
            elif e: char = "E"
            else: char = "."
            line += char
        print(line)

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: dump_map_20_ascii.py <file> <offset> <w> <h> [col/row]")
        sys.exit(1)
    
    f = sys.argv[1]
    off = int(sys.argv[2])
    w = int(sys.argv[3])
    h = int(sys.argv[4])
    cm = True
    if len(sys.argv) > 5 and sys.argv[5].lower() == 'row':
        cm = False
    
    dump_map_20(f, off, w, h, cm)
