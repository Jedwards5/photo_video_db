"""Enrichment pipeline: source-agnostic post-ingest processing."""

import argparse
import sqlite3
import time

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from .db.schema import init_db
from .faces import cluster_faces, detect_and_embed, label_faces
from .tagging import tag_photos
from .transcribe import transcribe_videos

# Nominatim usage policy: max 1 request per second
GEOCODE_DELAY = 1.1  # seconds between requests


def reverse_geocode(conn: sqlite3.Connection) -> None:
    """Reverse-geocode all media with coordinates that don't yet have a location."""
    rows = conn.execute("""
        SELECT m.id, m.latitude, m.longitude
        FROM media m
        LEFT JOIN locations l ON m.id = l.media_id
        WHERE m.latitude IS NOT NULL
          AND m.longitude IS NOT NULL
          AND l.id IS NULL
    """).fetchall()

    if not rows:
        print("No media with un-geocoded coordinates found.")
        return

    print(f"Found {len(rows)} media records to reverse-geocode.")

    geolocator = Nominatim(user_agent="personal-memories-archive")
    success = 0
    failed = 0

    for i, row in enumerate(rows):
        media_id, lat, lon = row["id"], row["latitude"], row["longitude"]

        try:
            location = geolocator.reverse(
                (lat, lon),
                exactly_one=True,
                language="en",
                timeout=10,
            )
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            print(f"  [{i+1}/{len(rows)}] media_id={media_id}: geocoder error — {e}")
            failed += 1
            time.sleep(GEOCODE_DELAY)
            continue

        if location and location.address:
            conn.execute(
                "INSERT OR IGNORE INTO locations (media_id, place_name) VALUES (?, ?)",
                (media_id, location.address),
            )
            success += 1
            print(f"  [{i+1}/{len(rows)}] media_id={media_id}: {location.address}")
        else:
            failed += 1
            print(f"  [{i+1}/{len(rows)}] media_id={media_id}: no result for ({lat}, {lon})")

        if i < len(rows) - 1:
            time.sleep(GEOCODE_DELAY)

    conn.commit()
    print(f"\nGeocoding complete. Success: {success}, Failed: {failed}")


def main():
    parser = argparse.ArgumentParser(description="Run enrichment steps on ingested media.")
    parser.add_argument(
        "--step",
        choices=["geocode", "detect-faces", "cluster-faces", "label-faces", "tag-photos", "transcribe"],
        required=True,
        help="Which enrichment step to run",
    )
    parser.add_argument(
        "--eps",
        type=float,
        default=0.7,
        help="DBSCAN eps for face clustering (lower = stricter, default: 0.7)",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=3,
        help="Minimum photos for a face cluster (default: 3)",
    )
    parser.add_argument(
        "--whisper-model",
        choices=["tiny", "base", "small", "medium", "large"],
        default=None,
        help="Whisper model size for transcription (default: base)",
    )
    args = parser.parse_args()

    conn = init_db()
    try:
        if args.step == "geocode":
            reverse_geocode(conn)
        elif args.step == "detect-faces":
            detect_and_embed(conn)
        elif args.step == "cluster-faces":
            cluster_faces(conn, eps=args.eps, min_samples=args.min_samples)
        elif args.step == "label-faces":
            label_faces(conn)
        elif args.step == "tag-photos":
            tag_photos(conn)
        elif args.step == "transcribe":
            transcribe_videos(conn, model_size=args.whisper_model)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
