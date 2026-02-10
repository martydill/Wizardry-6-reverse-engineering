
from pathlib import Path
from bane.data.pic_decoder import _decode_rle

def main():
    path = Path('gamedata/TITLEPAG.EGA')
    data = path.read_bytes()
    try:
        decompressed = _decode_rle(data)
        print(f"Decompressed size: {len(decompressed)}")
        if len(decompressed) > len(data):
            print("Successfully decompressed!")
            # Save a bit of it to see
            Path('decompressed.bin').write_bytes(decompressed)
    except Exception as e:
        print(f"RLE decompression failed: {e}")

if __name__ == "__main__":
    main()
