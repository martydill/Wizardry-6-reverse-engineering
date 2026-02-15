
from pathlib import Path

def main():
    data = Path('gamedata/TITLEPAG.EGA').read_bytes()
    for p in range(4):
        plane_data = data[p*8192 : p*8192 + 8000]
        set_bits = sum(bin(b).count('1') for b in plane_data)
        print(f"Plane {p}: {set_bits} bits set ({set_bits / (320*200) * 100:.1f}%)")

if __name__ == "__main__":
    main()
