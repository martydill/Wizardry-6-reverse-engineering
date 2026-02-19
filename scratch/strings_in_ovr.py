import re
import sys

def find_strings(filename, min_len=4):
    with open(filename, 'rb') as f:
        data = f.read()
    
    # Simple strings-like regex
    # We want to find ASCII strings
    pattern = rb'[\x20-\x7E]{' + str(min_len).encode() + rb',}'
    for match in re.finditer(pattern, data):
        try:
            s = match.group().decode('ascii')
            print(f"{match.start():04x}: {s}")
        except UnicodeDecodeError:
            pass

if __name__ == "__main__":
    find_strings(sys.argv[1])
