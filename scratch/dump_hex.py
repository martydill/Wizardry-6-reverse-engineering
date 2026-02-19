import sys

def dump_hex(filename, start, length):
    with open(filename, 'rb') as f:
        f.seek(start)
        data = f.read(length)
    
    for i in range(0, len(data), 16):
        row = data[i:i+16]
        hex_part = row.hex(' ')
        asc_part = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        print(f"{start+i:04x}: {hex_part:<48}  {asc_part}")

if __name__ == "__main__":
    dump_hex(sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16))
