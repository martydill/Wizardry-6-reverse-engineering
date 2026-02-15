"""Find 48-byte grayscale palettes in ega.drv."""

from pathlib import Path

def find_grayscale_palettes():
    path = Path("gamedata/ega.drv")
    if not path.exists():
        return

    data = path.read_bytes()
    
    for i in range(len(data) - 48):
        chunk = data[i:i+48]
        if all(b <= 63 for b in chunk):
            # Check how many colors are grayscale (R=G=B)
            triplets = [chunk[j:j+3] for j in range(0, 48, 3)]
            grays = sum(1 for t in triplets if t[0] == t[1] == t[2])
            
            # If at least 12 out of 16 colors are gray
            if grays >= 12:
                print(f"Potential grayscale palette at 0x{i:04x} ({grays}/16 grays):")
                for idx, t in enumerate(triplets):
                    print(f"  {idx:2d}: {list(t)}")
                print()

if __name__ == "__main__":
    find_grayscale_palettes()
