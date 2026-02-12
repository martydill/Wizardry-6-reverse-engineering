"""Create an annotated comparison image showing the decoded texture atlas.

This helps visualize what we've discovered about MAZEDATA format.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    import pygame


def create_annotated_atlas():
    """Create an annotated comparison showing the texture atlas structure."""
    print("Creating Annotated Texture Atlas Comparison")
    print("=" * 70)

    if not HAS_PIL:
        pygame.init()

    # Load and decode MAZEDATA.EGA
    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
    atlas = decoder.decode_planar(
        data[:32000],
        width=320,
        height=200,
        msb_first=True
    )

    if HAS_PIL:
        # Convert atlas to PIL image
        atlas_img = Image.new('RGB', (320, 200))
        pixels = []

        for y in range(200):
            for x in range(320):
                color_idx = atlas.get_pixel(x, y)
                if 0 <= color_idx < len(atlas.palette):
                    pixels.append(atlas.palette[color_idx])
                else:
                    pixels.append((0, 0, 0))

        atlas_img.putdata(pixels)

        # Scale up 3x
        atlas_scaled = atlas_img.resize((960, 600), Image.NEAREST)

        # Create larger canvas with annotation space
        canvas_width = 960 + 400  # Atlas + annotation space
        canvas_height = 600
        canvas = Image.new('RGB', (canvas_width, canvas_height), (20, 20, 20))

        # Paste atlas
        canvas.paste(atlas_scaled, (0, 0))

        # Draw band separators and labels
        draw = ImageDraw.Draw(canvas)

        # Band boundaries (scaled 3x)
        bands = [
            (0, 96, "Band 0: Dithered patterns", (100, 200, 100)),
            (96, 192, "Band 1: Wall patterns", (100, 200, 200)),
            (192, 288, "Band 2: Complex patterns", (200, 200, 100)),
            (288, 384, "Band 3: Varied patterns", (200, 150, 100)),
            (384, 480, "Band 4: CLEAR TILES!", (200, 100, 100)),
            (480, 600, "Band 5: Solid ceiling", (150, 100, 200)),
        ]

        # Draw horizontal lines and annotations
        for i, (y_start, y_end, label, color) in enumerate(bands):
            # Draw separator line
            draw.line([(0, y_end), (960, y_end)], fill=(255, 255, 0), width=2)

            # Draw label on atlas
            draw.text((5, y_start + 5), f"{i}", fill=(255, 255, 255))

            # Draw annotation on right side
            annotation_x = 970
            annotation_y = (y_start + y_end) // 2

            # Color indicator box
            draw.rectangle(
                [annotation_x, annotation_y - 10, annotation_x + 20, annotation_y + 10],
                fill=color,
                outline=(255, 255, 255)
            )

            # Label text
            draw.text(
                (annotation_x + 30, annotation_y - 10),
                label,
                fill=(255, 255, 255)
            )

        # Add title
        draw.text((10, 575), "MAZEDATA.EGA - Decoded Texture Atlas", fill=(255, 255, 255))
        draw.text((10, 555), "Format: 320x200 Sequential Planar EGA", fill=(200, 200, 200))

        # Add notes
        notes = [
            "SUCCESSFUL DECODING:",
            "",
            "✓ Format: Linear/Sequential Planar",
            "✓ Dimensions: 320×200 pixels",
            "✓ Colors: 16-color EGA palette",
            "✓ Organization: Horizontal bands",
            "",
            "Band 4 (y=128-160) has the",
            "clearest tile patterns for walls!",
            "",
            "These are AUTHENTIC 1990",
            "EGA textures - abstract patterns,",
            "not photorealistic bricks.",
        ]

        note_y = 20
        for note in notes:
            if note.startswith("✓") or note.startswith("SUCCESSFUL"):
                color = (100, 255, 100)
            else:
                color = (220, 220, 220)

            draw.text((970, note_y), note, fill=color)
            note_y += 20

        # Save
        output_path = Path("texture_atlas_annotated.png")
        canvas.save(output_path)
        print(f"Saved annotated atlas to: {output_path}")

    else:
        # Pygame version
        atlas_surf = pygame.Surface((320, 200))

        for y in range(200):
            for x in range(320):
                color_idx = atlas.get_pixel(x, y)
                if 0 <= color_idx < len(atlas.palette):
                    atlas_surf.set_at((x, y), atlas.palette[color_idx])

        atlas_scaled = pygame.transform.scale(atlas_surf, (960, 600))

        canvas = pygame.Surface((960 + 400, 600))
        canvas.fill((20, 20, 20))
        canvas.blit(atlas_scaled, (0, 0))

        # Draw annotations
        font = pygame.font.Font(None, 20)
        small_font = pygame.font.Font(None, 16)

        bands = [
            (0, 96, "Band 0: Dithered patterns", (100, 200, 100)),
            (96, 192, "Band 1: Wall patterns", (100, 200, 200)),
            (192, 288, "Band 2: Complex patterns", (200, 200, 100)),
            (288, 384, "Band 3: Varied patterns", (200, 150, 100)),
            (384, 480, "Band 4: CLEAR TILES!", (200, 100, 100)),
            (480, 600, "Band 5: Solid ceiling", (150, 100, 200)),
        ]

        for i, (y_start, y_end, label, color) in enumerate(bands):
            pygame.draw.line(canvas, (255, 255, 0), (0, y_end), (960, y_end), 2)

            text = font.render(str(i), True, (255, 255, 255))
            canvas.blit(text, (5, y_start + 5))

            annotation_x = 970
            annotation_y = (y_start + y_end) // 2

            pygame.draw.rect(canvas, color, (annotation_x, annotation_y - 10, 20, 20))
            pygame.draw.rect(canvas, (255, 255, 255), (annotation_x, annotation_y - 10, 20, 20), 1)

            text = small_font.render(label, True, (255, 255, 255))
            canvas.blit(text, (annotation_x + 30, annotation_y - 10))

        title = font.render("MAZEDATA.EGA - Decoded Texture Atlas", True, (255, 255, 255))
        canvas.blit(title, (10, 575))

        output_path = Path("texture_atlas_annotated.png")
        pygame.image.save(canvas, str(output_path))
        print(f"Saved annotated atlas to: {output_path}")

        pygame.quit()

    print("\n" + "=" * 70)
    print("Annotation complete!")
    print("=" * 70)


if __name__ == "__main__":
    create_annotated_atlas()
