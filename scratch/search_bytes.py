import sys

def search_bytes(filename, needle):
    with open(filename, 'rb') as f:
        data = f.read()
    
    pos = -1
    print(f"Searching for {needle.hex()} in {filename}")
    while True:
        pos = data.find(needle, pos + 1)
        if pos == -1: break
        print(f"  Found at file offset {pos:04x}")

if __name__ == "__main__":
    search_bytes(sys.argv[1], sys.argv[2].encode('ascii'))
