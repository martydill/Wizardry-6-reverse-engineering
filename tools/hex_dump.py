import sys

def hex_dump(filename, offset=0, length=1024):
    with open(filename, 'rb') as f:
        f.seek(offset)
        data = f.read(length)
    
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_str = chunk.hex(' ')
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
        print(f"{offset+i:04x}  {hex_str:<47}  {ascii_str}")

if __name__ == "__main__":
    file = sys.argv[1]
    offset = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    length = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    hex_dump(file, offset, length)
