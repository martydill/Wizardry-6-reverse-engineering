"""Test all plane order permutations to find the one that produces the most grays."""

import itertools
import sys
from pathlib import Path
from PIL import Image

# Add parent directory to path to import bane modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, Sprite

def find_best_order():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        return

    data = path.read_bytes()
    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
    
    best_order = None
    max_grays = -1
    
    orders = list(itertools.permutations(range(4)))
    print(f"Testing {len(orders)} permutations...")
    
    results = []
    
    for order in orders:
        # Decode first 32000 bytes
        sprite = decoder.decode_planar(data[:32000], 320, 200, plane_order=list(order))
        
        # Count grays (7: Light Gray, 8: Dark Gray, 15: White)
        gray_indices = {7, 8, 15}
        gray_count = sum(1 for p in sprite.pixels if p in gray_indices)
        
        results.append((order, gray_count))
        
        if gray_count > max_grays:
            max_grays = gray_count
            best_order = order

    # Sort results by gray count
    results.sort(key=lambda x: x[1], reverse=True)
    
    print("\nTop 5 plane orders for grays (7, 8, 15) with DEFAULT_16_PALETTE:")
    for order, count in results[:5]:
        percentage = count / (320 * 200) * 100
        print(f"  Order {order}: {count} pixels ({percentage:.1f}%)")

    # Now try with TITLEPAG_PALETTE grays (0, 1, 2, 3)
    from bane.data.sprite_decoder import TITLEPAG_PALETTE
    decoder_tp = EGADecoder(palette=TITLEPAG_PALETTE)
    results_tp = []
    
    for order in orders:
        sprite = decoder_tp.decode_planar(data[:32000], 320, 200, plane_order=list(order))
        gray_indices = {0, 1, 2, 3}
        gray_count = sum(1 for p in sprite.pixels if p in gray_indices)
        results_tp.append((order, gray_count))
        
    results_tp.sort(key=lambda x: x[1], reverse=True)
    print("\nTop 5 plane orders for grays (0, 1, 2, 3) with TITLEPAG_PALETTE:")
    for order, count in results_tp[:5]:
        percentage = count / (320 * 200) * 100
        print(f"  Order {order}: {count} pixels ({percentage:.1f}%)")

    # Save the best one from TITLEPAG search
    best_tp_order = results_tp[0][0]
    sprite = decoder_tp.decode_planar(data[:32000], 320, 200, plane_order=list(best_tp_order))
    img = Image.frombytes("RGB", (320, 200), sprite.to_rgb_bytes())
    img.save("output/mazedata_best_search.png")
    print(f"\nSaved best result to output/mazedata_best_search.png using order {best_tp_order}")

if __name__ == "__main__":
    find_best_order()
