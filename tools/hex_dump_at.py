"""Hex dump at offset."""
import sys
from pathlib import Path

def hex_dump(path, offset, length):
    data = Path(path).read_bytes()
    segment = data[offset:offset+length]
    for i in range(0, len(segment), 16):
        chunk = segment[i:i+16]
        hex_str = " ".join(f"{b:02x}" for b in chunk)
        ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"{offset+i:08x}  {hex_str:<48}  {ascii_str}")

if __name__ == "__main__":
    hex_dump(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
