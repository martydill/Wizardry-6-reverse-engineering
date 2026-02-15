"""Search for EGA grayscale register mappings in ega.drv."""

from pathlib import Path

def search_registers():
    path = Path("gamedata/ega.drv")
    if not path.exists():
        return

    data = path.read_bytes()
    grays = {0, 7, 56, 63}
    
    for i in range(len(data) - 16):
        chunk = data[i:i+16]
        if all(b in grays for b in chunk):
            # Exclude all zeros
            if len(set(chunk)) > 1:
                print(f"Potential EGA gray register mapping at 0x{i:04x}: {chunk.hex(' ')}")

if __name__ == "__main__":
    search_registers()
