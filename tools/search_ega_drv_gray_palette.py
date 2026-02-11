"""Find 48-byte palettes in ega.drv that are mostly grayscale."""

from pathlib import Path

def search_palettes():
    path = Path("gamedata/ega.drv")
    if not path.exists():
        return

    data = path.read_bytes()
    
    for i in range(len(data) - 48):
        chunk = data[i:i+48]
        if all(b <= 63 for b in chunk):
            # Calculate grayscale deviation
            triplets = [chunk[j:j+3] for j in range(0, 48, 3)]
            devs = [sum(abs(t[0]-t[k]) for k in range(1, 3)) for t in triplets]
            avg_dev = sum(devs) / 16
            
            # Count unique colors
            unique_colors = len(set(tuple(t) for t in triplets))
            
            # We want low deviation and more than 1 color
            if avg_dev < 5 and unique_colors > 2:
                print(f"Palette candidate at 0x{i:04x} (avg dev {avg_dev:.2f}, {unique_colors} unique):")
                for idx, t in enumerate(triplets):
                    print(f"  {idx:2d}: {list(t)}")
                print()

if __name__ == "__main__":
    search_palettes()
