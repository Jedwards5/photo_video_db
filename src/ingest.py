"""Ingest pipeline: parse source exports and populate the media table."""

import argparse
import sqlite3
from pathlib import Path

from .db.schema import init_db
from .sources.base import MediaRecord
from .sources.snapchat import SnapchatAdapter

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def insert_records(conn: sqlite3.Connection, records: list[MediaRecord]) -> tuple[int, int]:
    """Insert media records into the database. Returns (inserted, skipped) counts."""
    inserted = 0
    skipped = 0

    for record in records:
        try:
            conn.execute(
                """INSERT INTO media (filepath, source, media_type, timestamp, latitude, longitude, duration_seconds)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.filepath,
                    record.source,
                    record.media_type,
                    record.timestamp,
                    record.latitude,
                    record.longitude,
                    record.duration_seconds,
                ),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.commit()
    return inserted, skipped


def ingest_snapchat(conn: sqlite3.Connection, export_dir: Path | None = None) -> None:
    if export_dir is None:
        export_dir = DATA_DIR / "originals" / "snapchat"

    if not export_dir.exists():
        print(f"Snapchat export directory not found: {export_dir}")
        print("Place your Snapchat data export there and re-run.")
        return

    adapter = SnapchatAdapter(export_dir)
    records = adapter.parse_metadata()

    if not records:
        print("No media files found in Snapchat export.")
        return

    print(f"Found {len(records)} media files from Snapchat export.")
    inserted, skipped = insert_records(conn, records)
    print(f"Inserted: {inserted}, Skipped (already exists): {skipped}")


def main():
    parser = argparse.ArgumentParser(description="Ingest media from source exports into the database.")
    parser.add_argument(
        "--source",
        choices=["snapchat"],
        default="snapchat",
        help="Which source to ingest (default: snapchat)",
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=None,
        help="Override the default export directory path",
    )
    args = parser.parse_args()

    conn = init_db()
    try:
        if args.source == "snapchat":
            ingest_snapchat(conn, args.export_dir)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
