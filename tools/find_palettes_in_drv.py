"""Find palette-like structures in ega.drv."""

from pathlib import Path

def find_palettes():
    path = Path("gamedata/ega.drv")
    if not path.exists():
        print("File not found")
        return

    data = path.read_bytes()
    
    # Search for 48-byte blocks (16 * 3) where all values <= 63
    print("Potential 48-byte palettes (VGA 16-color, values 0-63):")
    for i in range(len(data) - 48):
        chunk = data[i:i+48]
        if all(b <= 63 for b in chunk):
            # Check for zero-heavy or too uniform blocks to avoid false positives
            if chunk.count(0) < 40:
                print(f"  Offset 0x{i:04x}: {chunk[:12].hex(' ')}...")

    # Search for 16-byte blocks where all values <= 63
    print("\nPotential 16-byte palettes (EGA registers, values 0-63):")
    for i in range(len(data) - 16):
        chunk = data[i:i+16]
        if all(b <= 63 for b in chunk):
            # Exclude very uniform or zero blocks
            if chunk.count(0) < 12 and len(set(chunk)) > 4:
                print(f"  Offset 0x{i:04x}: {chunk.hex(' ')}")

if __name__ == "__main__":
    find_palettes()
