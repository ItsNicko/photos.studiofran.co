"""Build 1200px JPEG copies and a photo manifest from photos/<event> folders.

Requires Pillow. Run with: python scripts/create_photo_thumbnails.py
"""

import json
import re
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
PHOTO_ROOT = ROOT / "photos"
MANIFEST_PATH = PHOTO_ROOT / "manifest.json"
MAX_SIZE = (1200, 1200)
JPEG_QUALITY = 76
Image.MAX_IMAGE_PIXELS = 100_000_000


def natural_key(path: Path) -> list[tuple[int, int | str]]:
    return [
        (1, int(part)) if part.isdigit() else (0, part.lower())
        for part in re.split(r"(\d+)", path.name)
    ]


def create_thumbnail(source: Path, destination: Path) -> None:
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.save(
            destination,
            format="JPEG",
            quality=JPEG_QUALITY,
            optimize=True,
            progressive=True,
        )


def main() -> None:
    manifest: dict[str, list[dict[str, str]]] = {}
    source_bytes = 0
    thumbnail_bytes = 0
    image_count = 0

    for event_folder in sorted(path for path in PHOTO_ROOT.iterdir() if path.is_dir()):
        photos = sorted(
            (
                path
                for path in event_folder.iterdir()
                if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}
            ),
            key=natural_key,
        )
        small_folder = event_folder / "small"
        small_folder.mkdir(exist_ok=True)
        photo_names = {photo.name for photo in photos}
        for stale_thumbnail in small_folder.iterdir():
            if (
                stale_thumbnail.is_file()
                and stale_thumbnail.suffix.lower() in {".jpg", ".jpeg"}
                and stale_thumbnail.name not in photo_names
            ):
                stale_thumbnail.unlink()

        manifest[event_folder.name] = []

        for photo in photos:
            thumbnail = small_folder / photo.name
            create_thumbnail(photo, thumbnail)
            manifest[event_folder.name].append(
                {
                    "filename": photo.name,
                    "caption": photo.stem.replace("-", " ").replace("_", " "),
                }
            )
            source_bytes += photo.stat().st_size
            thumbnail_bytes += thumbnail.stat().st_size
            image_count += 1

    if not manifest:
        raise FileNotFoundError(f"No event folders found in {PHOTO_ROOT}")

    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    saved_percent = 100 * (1 - thumbnail_bytes / source_bytes) if source_bytes else 0
    print(
        f"Created {image_count} thumbnails across {len(manifest)} event folders. "
        f"{source_bytes / 1_000_000:.1f} MB originals -> "
        f"{thumbnail_bytes / 1_000_000:.1f} MB thumbnails "
        f"({saved_percent:.1f}% smaller)."
    )
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
