"""Thumbnail generation for all media in the database.

Generates a JPEG thumbnail for every photo and video:
  - Photos: Pillow resize to fit within THUMB_SIZE x THUMB_SIZE
  - Videos: ffmpeg extracts the first frame

Output: data/processed/thumbnails/{media_id}.jpg
Run once before starting the web server: python -m src.thumbnails
Re-running is safe — already-generated thumbnails are skipped.
"""

import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from PIL import Image

from .db.schema import init_db

THUMB_SIZE = 400  # max width or height in pixels
THUMB_DIR = Path("data/processed/thumbnails")
THUMB_QUALITY = 85


def _thumbnail_path(media_id: int) -> Path:
    return THUMB_DIR / f"{media_id}.jpg"


def _generate_photo_thumb(src: Path, dest: Path) -> bool:
    try:
        with Image.open(src) as img:
            img.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)
            if img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")
            dest.parent.mkdir(parents=True, exist_ok=True)
            img.save(dest, "JPEG", quality=THUMB_QUALITY)
        return True
    except Exception as e:
        print(f"    [photo error] {src.name}: {e}")
        return False


def _generate_video_thumb(src: Path, dest: Path) -> bool:
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(src),
                "-vframes", "1",
                "-vf", f"scale={THUMB_SIZE}:{THUMB_SIZE}:force_original_aspect_ratio=decrease",
                "-q:v", "2",
                str(dest),
            ],
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"    [video timeout] {src.name}")
        return False
    except Exception as e:
        print(f"    [video error] {src.name}: {e}")
        return False


def generate_thumbnails(conn: sqlite3.Connection) -> None:
    if not shutil.which("ffmpeg"):
        print("WARNING: ffmpeg not found in PATH — video thumbnails will be skipped.")
        print("         Add ffmpeg to PATH or run from PowerShell where ffmpeg is available.")

    rows = conn.execute(
        "SELECT id, filepath, media_type FROM media ORDER BY timestamp DESC"
    ).fetchall()

    THUMB_DIR.mkdir(parents=True, exist_ok=True)

    total = len(rows)
    skipped = done = failed = 0

    print(f"Generating thumbnails for {total} media files...")

    for i, row in enumerate(rows, 1):
        media_id, filepath, media_type = row["id"], row["filepath"], row["media_type"]
        dest = _thumbnail_path(media_id)

        if dest.exists():
            skipped += 1
            continue

        src = Path(filepath)
        if not src.exists():
            print(f"  [{i}/{total}] MISSING: {src.name}")
            failed += 1
            continue

        if media_type == "video":
            if not shutil.which("ffmpeg"):
                failed += 1
                continue
            success = _generate_video_thumb(src, dest)
        else:
            success = _generate_photo_thumb(src, dest)

        if success:
            done += 1
        else:
            failed += 1

        if i % 100 == 0 or i == total:
            print(f"  {i}/{total} — generated: {done}, skipped: {skipped}, failed: {failed}")

    print(f"\nDone. Generated: {done}, Already existed: {skipped}, Failed: {failed}")


def main():
    conn = init_db()
    try:
        generate_thumbnails(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
