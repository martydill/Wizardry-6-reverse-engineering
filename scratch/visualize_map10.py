def decode_4bit_map(data, width, height, q_width, q_height):
    map_grid = [[0 for _ in range(width)] for _ in range(height)]
    
    bytes_per_q = (q_width * q_height) // 2
    
    for qy in range(height // q_height):
        for qx in range(width // q_width):
            q_idx = qy * (width // q_width) + qx
            q_start = q_idx * bytes_per_q
            q_data = data[q_start : q_start + bytes_per_q]
            
            for i in range(q_width * q_height):
                byte_idx = i // 2
                nibble = i % 2
                val = q_data[byte_idx]
                if nibble == 0:
                    val = val & 0x0F
                else:
                    val = (val >> 4) & 0x0F
                
                rx = i % q_width
                ry = i // q_width
                
                gx = qx * q_width + rx
                gy = qy * q_height + ry
                map_grid[gy][gx] = val
                
    return map_grid

def print_map(grid):
    for row in grid:
        print(" ".join(f"{v:X}" for v in row))

with open('gamedata/newgame.dbs', 'rb') as f:
    f.seek(0x7D22)
    data = f.read(128)

print("Modified Map 10 Features:")
grid = decode_4bit_map(data, 16, 16, 8, 8)
print_map(grid)

with open('gamedata/newgame0.dbs', 'rb') as f:
    f.seek(0x7D22)
    data0 = f.read(128)

print("\nOriginal Map 10 Features:")
grid0 = decode_4bit_map(data0, 16, 16, 8, 8)
print_map(grid0)
