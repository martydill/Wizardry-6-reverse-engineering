"""Dump images from MAZEDATA.EGA using the metadata region as descriptors.

Heuristic format (per 6-byte records):
  - u16 offset (relative to base)
  - u8 width_units
  - u8 height_units
  - u16 flags/unknown

Widths/heights are multiplied by unit size (default 4 pixels). Records
that do not produce 8x8-aligned sizes are skipped.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bane.data.sprite_decoder import EGADecoder, Sprite  # noqa: E402

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - runtime dependency
    raise SystemExit("Pillow is required: python -m pip install pillow") from exc


@dataclass(frozen=True)
class Descriptor:
    """Parsed metadata record."""

    index: int
    meta_offset: int
    data_offset: int
    width: int
    height: int
    flags: int


@dataclass(frozen=True)
class TileDump:
    """Decoded tile plus metadata for sorting/selection."""

    index: int
    data_offset: int
    width: int
    height: int
    bytes_len: int
    score: float
    sprite: Sprite


def parse_descriptors(
    metadata: bytes,
    base_offset: int,
    unit_px: int,
    record_size: int = 6,
) -> list[Descriptor]:
    """Parse metadata records into descriptors."""
    descriptors: list[Descriptor] = []

    if record_size != 6:
        raise ValueError("Only 6-byte records are supported for now.")

    for i in range(0, len(metadata) - (record_size - 1), record_size):
        off = metadata[i] | (metadata[i + 1] << 8)
        width_units = metadata[i + 2]
        height_units = metadata[i + 3]
        flags = metadata[i + 4] | (metadata[i + 5] << 8)

        if width_units == 0 or height_units == 0:
            continue

        width = width_units * unit_px
        height = height_units * unit_px

        if width % 8 != 0 or height % 8 != 0:
            continue

        data_offset = base_offset + off
        descriptors.append(
            Descriptor(
                index=i // record_size,
                meta_offset=i,
                data_offset=data_offset,
                width=width,
                height=height,
                flags=flags,
            )
        )

    return descriptors


def create_grayscale_palette() -> list[tuple[int, int, int]]:
    """Map 4-bit values to grayscale RGB."""
    palette: list[tuple[int, int, int]] = []
    for i in range(16):
        gray = int((i / 15.0) * 255)
        palette.append((gray, gray, gray))
    return palette


def sprite_to_image(sprite: Sprite) -> Image.Image:
    """Convert a Sprite to a PIL image."""
    img = Image.new("RGB", (sprite.width, sprite.height))
    pixels: list[tuple[int, int, int]] = []
    for y in range(sprite.height):
        for x in range(sprite.width):
            idx = sprite.get_pixel(x, y)
            if 0 <= idx < len(sprite.palette):
                pixels.append(sprite.palette[idx])
            else:
                pixels.append((0, 0, 0))
    img.putdata(pixels)
    return img


def compute_score(sprite: Sprite) -> float:
    """Compute a contrast-like score to surface likely wall textures."""
    values = sprite.pixels
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    unique = len(set(values))
    return var + unique * 0.2


def save_contact_sheet(
    tiles: list[TileDump],
    out_path: Path,
    grid_cols: int,
    scale: int,
) -> None:
    """Save a contact sheet from TileDump list."""
    if not tiles:
        return
    tile_w = tiles[0].width
    tile_h = tiles[0].height
    grid_rows = (len(tiles) + grid_cols - 1) // grid_cols
    img = Image.new("RGB", (tile_w * grid_cols, tile_h * grid_rows))
    for idx, tile in enumerate(tiles):
        x = (idx % grid_cols) * tile_w
        y = (idx // grid_cols) * tile_h
        img.paste(sprite_to_image(tile.sprite), (x, y))
    if scale > 1:
        img = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    img.save(out_path)


def dump_images(
    path: Path,
    output_dir: Path,
    base_offset: int,
    unit_px: int,
    max_images: int | None,
    scale: int,
) -> None:
    """Decode and dump images from MAZEDATA.EGA."""
    data = path.read_bytes()
    if base_offset <= 0 or base_offset >= len(data):
        raise ValueError("Base offset is outside file bounds.")

    metadata = data[:base_offset]
    descriptors = parse_descriptors(metadata, base_offset, unit_px)

    output_dir.mkdir(parents=True, exist_ok=True)

    decoder = EGADecoder(palette=create_grayscale_palette())

    csv_path = output_dir / "index.csv"
    with csv_path.open("w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "index",
                "meta_offset",
                "data_offset",
                "width",
                "height",
                "flags",
                "bytes",
                "score",
                "file",
            ]
        )

        dumped = 0
        tiles_for_sheets: list[TileDump] = []
        for desc in descriptors:
            bytes_per_plane = (desc.width * desc.height) // 8
            tile_bytes = bytes_per_plane * 4

            if desc.data_offset + tile_bytes > len(data):
                continue

            payload = data[desc.data_offset : desc.data_offset + tile_bytes]
            sprite = decoder.decode_tiled_planar(
                payload,
                width=desc.width,
                height=desc.height,
                msb_first=True,
                row_major=True,
            )
            score = compute_score(sprite)

            img = sprite_to_image(sprite)
            if scale > 1:
                img = img.resize((desc.width * scale, desc.height * scale), Image.NEAREST)

            filename = f"tile_{desc.index:04d}_{desc.width}x{desc.height}_off{desc.data_offset:05X}.png"
            img_path = output_dir / filename
            img.save(img_path)

            writer.writerow(
                [
                    desc.index,
                    f"0x{desc.meta_offset:04X}",
                    f"0x{desc.data_offset:05X}",
                    desc.width,
                    desc.height,
                    f"0x{desc.flags:04X}",
                    tile_bytes,
                    f"{score:.3f}",
                    filename,
                ]
            )

            tiles_for_sheets.append(
                TileDump(
                    index=desc.index,
                    data_offset=desc.data_offset,
                    width=desc.width,
                    height=desc.height,
                    bytes_len=tile_bytes,
                    score=score,
                    sprite=sprite,
                )
            )

            dumped += 1
            if max_images is not None and dumped >= max_images:
                break

    # Contact sheets
    if tiles_for_sheets:
        first_tiles = tiles_for_sheets[:64]
        save_contact_sheet(
            first_tiles,
            output_dir / "grid_first.png",
            grid_cols=8,
            scale=scale,
        )
        best_tiles = sorted(tiles_for_sheets, key=lambda t: t.score, reverse=True)[:64]
        save_contact_sheet(
            best_tiles,
            output_dir / "grid_best.png",
            grid_cols=8,
            scale=scale,
        )

    print(f"Parsed descriptors: {len(descriptors)}")
    print(f"Dumped images: {dumped}")
    print(f"Index: {csv_path}")


def dump_raw_tiles(
    data: bytes,
    output_dir: Path,
    start: int,
    end: int,
    tile_width: int,
    tile_height: int,
    max_tiles: int | None,
    scale: int,
) -> None:
    """Dump raw tiled-planar tiles from a byte range."""
    if start < 0 or start >= len(data):
        raise ValueError("Start offset is outside file bounds.")
    if end <= start or end > len(data):
        raise ValueError("End offset is outside file bounds.")

    bytes_per_plane = (tile_width * tile_height) // 8
    tile_bytes = bytes_per_plane * 4
    available = end - start
    count = available // tile_bytes
    if max_tiles is not None:
        count = min(count, max_tiles)

    output_dir.mkdir(parents=True, exist_ok=True)
    decoder = EGADecoder(palette=create_grayscale_palette())

    tiles_for_sheets: list[TileDump] = []
    csv_path = output_dir / "index.csv"
    with csv_path.open("w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "index",
                "data_offset",
                "width",
                "height",
                "bytes",
                "score",
                "file",
            ]
        )

        for i in range(count):
            data_offset = start + i * tile_bytes
            payload = data[data_offset : data_offset + tile_bytes]
            sprite = decoder.decode_tiled_planar(
                payload,
                width=tile_width,
                height=tile_height,
                msb_first=True,
                row_major=True,
            )
            score = compute_score(sprite)
            img = sprite_to_image(sprite)
            if scale > 1:
                img = img.resize((tile_width * scale, tile_height * scale), Image.NEAREST)
            filename = f"tile_{i:04d}_{tile_width}x{tile_height}_off{data_offset:05X}.png"
            img.save(output_dir / filename)
            writer.writerow(
                [
                    i,
                    f"0x{data_offset:05X}",
                    tile_width,
                    tile_height,
                    tile_bytes,
                    f"{score:.3f}",
                    filename,
                ]
            )
            tiles_for_sheets.append(
                TileDump(
                    index=i,
                    data_offset=data_offset,
                    width=tile_width,
                    height=tile_height,
                    bytes_len=tile_bytes,
                    score=score,
                    sprite=sprite,
                )
            )

    if tiles_for_sheets:
        save_contact_sheet(
            tiles_for_sheets[:64],
            output_dir / "grid_first.png",
            grid_cols=8,
            scale=scale,
        )
        best_tiles = sorted(tiles_for_sheets, key=lambda t: t.score, reverse=True)[:64]
        save_contact_sheet(
            best_tiles,
            output_dir / "grid_best.png",
            grid_cols=8,
            scale=scale,
        )

    print(f"Raw tiles dumped: {count}")
    print(f"Index: {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump MAZEDATA.EGA images.")
    parser.add_argument(
        "--gamedata",
        type=Path,
        default=Path("gamedata"),
        help="Path to gamedata directory.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("output") / "mazedata_dump",
        help="Output directory.",
    )
    parser.add_argument(
        "--base",
        type=lambda s: int(s, 0),
        default=0x2A00,
        help="Base offset for tile payload (default 0x2A00).",
    )
    parser.add_argument(
        "--unit",
        type=int,
        default=4,
        help="Pixel units per width/height byte (default 4).",
    )
    parser.add_argument(
        "--unit-list",
        type=str,
        default="4",
        help="Comma-separated unit sizes for brute force (e.g. 2,4,8).",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="Maximum number of images to dump.",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=2,
        help="Scale factor for output images.",
    )
    parser.add_argument(
        "--mode",
        choices=["descriptors", "raw", "both"],
        default="both",
        help="Dump mode.",
    )
    parser.add_argument(
        "--base-list",
        type=str,
        default="0x2A00",
        help="Comma-separated base offsets for descriptor mode.",
    )
    parser.add_argument(
        "--raw-start",
        type=lambda s: int(s, 0),
        default=0x2A00,
        help="Raw dump start offset.",
    )
    parser.add_argument(
        "--raw-end",
        type=lambda s: int(s, 0),
        default=0,
        help="Raw dump end offset (0 = EOF).",
    )
    parser.add_argument(
        "--tile-sizes",
        type=str,
        default="32x32,64x32,32x64,16x16,8x8",
        help="Comma-separated raw tile sizes WxH.",
    )
    args = parser.parse_args()

    path = args.gamedata / "MAZEDATA.EGA"
    if not path.exists():
        path = args.gamedata / "mazedata.ega"
    if not path.exists():
        raise SystemExit(f"MAZEDATA.EGA not found in {args.gamedata}")

    data = path.read_bytes()
    raw_end = args.raw_end or len(data)

    base_list = [int(x.strip(), 0) for x in args.base_list.split(",") if x.strip()]
    unit_list = [int(x.strip()) for x in args.unit_list.split(",") if x.strip()]

    if args.mode in ("descriptors", "both"):
        for base in base_list:
            for unit in unit_list:
                out_dir = args.out / f"desc_base{base:05X}_u{unit}"
                dump_images(
                    path=path,
                    output_dir=out_dir,
                    base_offset=base,
                    unit_px=unit,
                    max_images=args.max,
                    scale=args.scale,
                )

    if args.mode in ("raw", "both"):
        sizes: list[tuple[int, int]] = []
        for part in args.tile_sizes.split(","):
            part = part.strip()
            if not part:
                continue
            if "x" not in part:
                raise SystemExit(f"Invalid tile size: {part}")
            w_str, h_str = part.split("x", 1)
            sizes.append((int(w_str), int(h_str)))

        for w, h in sizes:
            out_dir = args.out / f"raw_{w}x{h}_from{args.raw_start:05X}_to{raw_end:05X}"
            dump_raw_tiles(
                data=data,
                output_dir=out_dir,
                start=args.raw_start,
                end=raw_end,
                tile_width=w,
                tile_height=h,
                max_tiles=args.max,
                scale=args.scale,
            )


if __name__ == "__main__":
    main()
