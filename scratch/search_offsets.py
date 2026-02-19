import sys

def search_offsets(filename, offsets):
    with open(filename, 'rb') as f:
        data = f.read()
    
    for offset in offsets:
        # Check both little-endian 2-byte and maybe larger if needed
        needle = offset.to_bytes(2, byteorder='little')
        pos = -1
        print(f"Searching for offset {offset:04x} (bytes {needle.hex()})")
        while True:
            pos = data.find(needle, pos + 1)
            if pos == -1: break
            print(f"  Found at file offset {pos:04x}")
            # Show context
            start = max(0, pos - 4)
            end = min(len(data), pos + 6)
            print(f"    Context: {data[start:end].hex()}")

if __name__ == "__main__":
    offsets = [int(x, 16) for x in sys.argv[2:]]
    search_offsets(sys.argv[1], offsets)
