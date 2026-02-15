"""MAZEDATA.EGA texture atlas decoder.

Decodes the Wizardry 6 wall texture atlas from MAZEDATA.EGA.
"""

from pathlib import Path
from PIL import Image
import sys

# Add parent directory to path to import bane modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, Sprite


def decode_mazedata(input_path: str | Path, output_path: str | Path | None = None) -> Sprite:
    """Decode MAZEDATA.EGA texture atlas.

    Args:
        input_path: Path to MAZEDATA.EGA file
        output_path: Optional path to save PNG (default: output/mazedata_atlas.png)

    Returns:
        Decoded Sprite containing the 320×200 texture atlas
    """
    input_path = Path(input_path)
    if output_path is None:
        output_path = Path("output/mazedata_atlas.png")
    else:
        output_path = Path(output_path)

    # Read file
    data = input_path.read_bytes()
    file_size = len(data)

    print(f"MAZEDATA.EGA Decoder")
    print("=" * 70)
    print(f"Input: {input_path}")
    print(f"File size: {file_size:,} bytes")
    print()

    # MAZEDATA.EGA uses DEFAULT_16_PALETTE (no palette header!)
    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)

    # Decode first 32,000 bytes as 320×200 sequential planar image
    atlas_data = data[:32000]
    print(f"Decoding main atlas: 32,000 bytes")
    print(f"Format: Sequential planar (plane0, plane1, plane2, plane3)")
    print(f"Dimensions: 320×200 pixels, 16 colors")
    print()

    atlas = decoder.decode_planar(
        atlas_data,
        width=320,
        height=200,
        msb_first=True
    )

    # Save as PNG
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.frombytes("RGB", (atlas.width, atlas.height), atlas.to_rgb_bytes())
    img.save(output_path)

    print(f"Saved atlas: {output_path}")
    print(f"Image size: {atlas.width}×{atlas.height}")
    print()

    # Report on remaining data
    remaining = file_size - 32000
    print(f"Remaining data: {remaining:,} bytes ({remaining/32000:.1f}× main atlas)")
    print(f"  Could contain {remaining//32000} additional 320×200 images")
    print(f"  or {remaining//32} 8×8 tiles")
    print()

    return atlas


def decode_ega_image(input_path: str | Path, output_path: str | Path | None = None) -> Sprite:
    """Decode any .EGA file (TITLEPAG, DRAGONSC, GRAVEYRD, etc.) with palette header.

    Args:
        input_path: Path to .EGA file
        output_path: Optional path to save PNG

    Returns:
        Decoded Sprite
    """
    input_path = Path(input_path)
    if output_path is None:
        output_path = Path(f"output/{input_path.stem.lower()}.png")
    else:
        output_path = Path(output_path)

    # Read file
    data = input_path.read_bytes()

    print(f"{input_path.name} Decoder")
    print("=" * 70)
    print(f"File size: {len(data):,} bytes")

    # Extract VGA palette from first 768 bytes
    palette = []
    for i in range(16):
        r = min(255, data[i * 3] * 4)  # VGA palette is 0-63, scale to 0-252
        g = min(255, data[i * 3 + 1] * 4)
        b = min(255, data[i * 3 + 2] * 4)
        palette.append((r, g, b))

    print(f"Palette extracted: 16 colors from VGA palette header")

    # Decode sequential planar data from byte 768 onward
    decoder = EGADecoder(palette=palette)
    image_data = data[768:]

    sprite = decoder.decode_planar(
        image_data,
        width=320,
        height=200,
        msb_first=True
    )

    # Save as PNG
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.frombytes("RGB", (sprite.width, sprite.height), sprite.to_rgb_bytes())
    img.save(output_path)

    print(f"Saved: {output_path}")
    print()

    return sprite


def main():
    """Decode all .EGA files."""
    # Try to find gamedata directory (might be in parent dir if running from tools/)
    gamedata_dir = Path("gamedata")
    if not gamedata_dir.exists():
        gamedata_dir = Path("../gamedata")
    if not gamedata_dir.exists():
        print("Error: Cannot find gamedata directory")
        return

    # Decode MAZEDATA.EGA (no palette header)
    mazedata_path = gamedata_dir / "MAZEDATA.EGA"
    if mazedata_path.exists():
        decode_mazedata(mazedata_path)
    else:
        print(f"Warning: {mazedata_path} not found")
        print()

    # Decode other .EGA files (with palette headers)
    for filename in ["TITLEPAG.EGA", "DRAGONSC.EGA", "GRAVEYRD.EGA"]:
        ega_path = gamedata_dir / filename
        if ega_path.exists():
            decode_ega_image(ega_path)
        else:
            print(f"Warning: {ega_path} not found")
            print()


if __name__ == "__main__":
    main()
