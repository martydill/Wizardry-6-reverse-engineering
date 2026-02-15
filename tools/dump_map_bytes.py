import sys

def dump_map(filename):
    with open(filename, 'rb') as f:
        data = f.read()
    
    print("Byte 3:")
    for r in range(20):
        row = []
        for c in range(20):
            cell_idx = r * 20 + c
            offset = cell_idx * 8 + 3
            if offset < len(data):
                val = data[offset]
                row.append(f"{val:02x}")
            else:
                row.append("..")
        print(" ".join(row))
    
    print("\nByte 5:")
    for r in range(20):
        row = []
        for c in range(20):
            cell_idx = r * 20 + c
            offset = cell_idx * 8 + 5
            if offset < len(data):
                val = data[offset]
                row.append(f"{val:02x}")
            else:
                row.append("..")
        print(" ".join(row))

if __name__ == "__main__":
    dump_map(sys.argv[1])
