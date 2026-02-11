"""Compare different Wizardry 6 graphics formats to understand MAZEDATA textures."""

from pathlib import Path
from PIL import Image
import sys

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE
from bane.data.pic_decoder import decode_pic_file, decode_pic_frames

def decode_monster_pics():
    """Decode several monster .PIC files to see how they look."""
    gamedata = Path("gamedata")
    output_dir = Path("output/monsters")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Decoding Monster .PIC Files")
    print("=" * 70)

    # Decode a few monsters
    for mon_num in [0, 1, 2, 13, 20]:
        pic_path = gamedata / f"MON{mon_num:02d}.PIC"
        if not pic_path.exists():
            continue

        print(f"\n{pic_path.name}:")

        try:
            # Get all frames
            data = pic_path.read_bytes()
            frames = decode_pic_frames(data)

            print(f"  Frames: {len(frames)}")

            for i, sprite in enumerate(frames):
                print(f"    Frame {i}: {sprite.width}×{sprite.height} pixels")

                # Save the frame
                img = Image.frombytes("RGB", (sprite.width, sprite.height), sprite.to_rgb_bytes())

                # Scale up 2x for easier viewing
                img = img.resize((sprite.width * 2, sprite.height * 2), Image.NEAREST)

                output_path = output_dir / f"mon{mon_num:02d}_frame{i}.png"
                img.save(output_path)
                print(f"      Saved: {output_path.name}")

        except Exception as e:
            print(f"  Error: {e}")


def compare_ega_files():
    """Look at the successfully decoded .EGA files."""
    print("\n" + "=" * 70)
    print("Comparing .EGA Files")
    print("=" * 70)

    gamedata = Path("gamedata")

    # These we can decode properly
    ega_files = ["TITLEPAG.EGA", "DRAGONSC.EGA", "GRAVEYRD.EGA"]

    for filename in ega_files:
        path = gamedata / filename
        if not path.exists():
            continue

        print(f"\n{filename}:")
        data = path.read_bytes()
        print(f"  Size: {len(data)} bytes")

        # Extract palette
        palette = []
        for i in range(16):
            r = min(255, data[i * 3] * 4)
            g = min(255, data[i * 3 + 1] * 4)
            b = min(255, data[i * 3 + 2] * 4)
            palette.append((r, g, b))

        print(f"  Palette: Custom (from header)")

        # Show palette colors
        print("  Colors: ", end="")
        for i, (r, g, b) in enumerate(palette[:8]):
            print(f"#{r:02X}{g:02X}{b:02X} ", end="")
        print("...")


def analyze_mazedata_atlas():
    """Analyze the MAZEDATA texture atlas in detail."""
    print("\n" + "=" * 70)
    print("Analyzing MAZEDATA.EGA Texture Atlas")
    print("=" * 70)

    gamedata = Path("gamedata")
    path = gamedata / "MAZEDATA.EGA"
    data = path.read_bytes()

    print(f"\nFile size: {len(data)} bytes")
    print(f"Main atlas: 32,000 bytes (320×200)")
    print(f"Extra data: {len(data) - 32000} bytes")

    # Decode the atlas
    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
    atlas = decoder.decode_planar(data[:32000], width=320, height=200, msb_first=True)

    print(f"\nAtlas decoded: {atlas.width}×{atlas.height}")

    # Sample different horizontal bands
    print("\nAnalyzing horizontal bands (textures arranged in rows):")

    band_height = 10
    num_bands = 20

    for band_idx in range(num_bands):
        y_start = band_idx * band_height
        y_end = min(y_start + band_height, atlas.height)

        # Count unique colors in this band
        colors = set()
        for y in range(y_start, y_end):
            for x in range(atlas.width):
                colors.add(atlas.get_pixel(x, y))

        print(f"  Band {band_idx:2d} (y={y_start:3d}-{y_end:3d}): {len(colors):2d} colors", end="")

        # Extract and save this band
        band_pixels = []
        for y in range(y_start, y_end):
            for x in range(atlas.width):
                band_pixels.append(atlas.get_pixel(x, y))

        from bane.data.sprite_decoder import Sprite
        band_sprite = Sprite(
            width=atlas.width,
            height=y_end - y_start,
            pixels=band_pixels,
            palette=atlas.palette
        )

        # Scale up vertically for easier viewing
        scaled_pixels = []
        scale = 4
        for y in range(band_sprite.height):
            row = band_sprite.pixels[y * band_sprite.width:(y + 1) * band_sprite.width]
            for _ in range(scale):
                scaled_pixels.extend(row)

        scaled_sprite = Sprite(
            width=band_sprite.width,
            height=band_sprite.height * scale,
            pixels=scaled_pixels,
            palette=band_sprite.palette
        )

        img = Image.frombytes("RGB", (scaled_sprite.width, scaled_sprite.height), scaled_sprite.to_rgb_bytes())
        output_path = Path(f"output/mazedata_band_{band_idx:02d}_y{y_start:03d}.png")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)
        print(f" -> {output_path.name}")


def extract_sample_textures():
    """Try to extract what look like individual textures from the atlas."""
    print("\n" + "=" * 70)
    print("Extracting Sample Textures")
    print("=" * 70)

    gamedata = Path("gamedata")
    path = gamedata / "MAZEDATA.EGA"
    data = path.read_bytes()

    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
    atlas = decoder.decode_planar(data[:32000], width=320, height=200, msb_first=True)

    # Try to extract textures at various positions
    # Common wall texture sizes might be 32x32, 16x16, 64x32, etc.

    test_regions = [
        ("top_left_32x32", 0, 0, 32, 32),
        ("32x32_at_32", 32, 0, 32, 32),
        ("32x32_at_64", 64, 0, 32, 32),
        ("64x32_at_0", 0, 0, 64, 32),
        ("full_width_band_0_10", 0, 0, 320, 10),
        ("full_width_band_10_20", 0, 10, 320, 10),
    ]

    from bane.data.sprite_decoder import Sprite

    for name, x, y, w, h in test_regions:
        pixels = []
        for dy in range(h):
            for dx in range(w):
                px = atlas.get_pixel(x + dx, y + dy)
                pixels.append(px)

        sprite = Sprite(width=w, height=h, pixels=pixels, palette=atlas.palette)

        # Scale up for viewing
        scale = 4 if w <= 64 else 1
        if scale > 1:
            scaled = sprite.scale(scale)
        else:
            scaled = sprite

        img = Image.frombytes("RGB", (scaled.width, scaled.height), scaled.to_rgb_bytes())
        output_path = Path(f"output/texture_sample_{name}.png")
        img.save(output_path)

        print(f"  {name}: {w}×{h} -> {output_path.name}")


if __name__ == "__main__":
    decode_monster_pics()
    compare_ega_files()
    analyze_mazedata_atlas()
    extract_sample_textures()

    print("\n" + "=" * 70)
    print("Analysis complete! Check the output/ directory for images.")
    print("=" * 70)
