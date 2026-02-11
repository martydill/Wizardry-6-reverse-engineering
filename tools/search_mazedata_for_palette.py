"""Search for palette in MAZEDATA.EGA."""

from pathlib import Path

def search_palette():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        return

    data = path.read_bytes()
    
    # Check start and end of file especially
    for i in range(len(data) - 48):
        # Limit search to avoid too much output, but check header and trailer
        if i > 2000 and i < len(data) - 2000:
            continue
            
        chunk = data[i:i+48]
        if all(b <= 63 for b in chunk):
            triplets = [chunk[j:j+3] for j in range(0, 48, 3)]
            grays = sum(1 for t in triplets if t[0] == t[1] == t[2])
            if grays >= 8:
                print(f"Potential palette at 0x{i:04x} ({grays}/16 grays):")
                print(f"  {chunk.hex(' ')}")

if __name__ == "__main__":
    search_palette()
