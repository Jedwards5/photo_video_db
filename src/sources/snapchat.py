"""Snapchat source adapter.

Parses a Snapchat data export (memories_history.json + media files)
into normalized MediaRecord objects.

Export structure:
  export_dir/
    json/memories_history.json   — metadata with dates, GPS, media type
    memories/                    — media files named {date}_{uuid}-main.{ext}

JSON entries are matched to files via UUID: the 'sid' parameter in the
JSON download URL corresponds to the UUID embedded in each filename.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .base import MediaRecord, SourceAdapter

MEDIA_EXTENSIONS = {
    "photo": {".jpg", ".jpeg", ".png", ".webp"},
    "video": {".mp4", ".mov"},
}

# Regex to extract UUID from filenames like "2016-03-11_05617bea-111e-4a44-b0f1-e4a91a0065cd-main.jpg"
FILENAME_UUID_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})-main",
    re.IGNORECASE,
)


def _parse_location(location_str: str) -> tuple[float | None, float | None]:
    """Parse 'Latitude, Longitude: 37.574013, -77.464485' into (lat, lon)."""
    match = re.search(r"(-?\d+\.?\d*),\s*(-?\d+\.?\d*)", location_str)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None


def _parse_timestamp(date_str: str) -> str:
    """Convert '2025-06-15 02:18:13 UTC' to ISO 8601 format."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %Z")
        return dt.replace(tzinfo=timezone.utc).isoformat()
    except ValueError:
        return date_str


def _extract_sid(url: str) -> str | None:
    """Extract the 'sid' parameter from a Snapchat download URL."""
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        sid = params.get("sid", [None])[0]
        return sid.lower() if sid else None
    except Exception:
        return None


def _extract_uuid_from_filename(filename: str) -> str | None:
    """Extract UUID from a filename like '2016-03-11_05617bea-...-main.jpg'."""
    match = FILENAME_UUID_RE.search(filename)
    return match.group(1).lower() if match else None


class SnapchatAdapter(SourceAdapter):
    def __init__(self, export_dir: Path):
        self.export_dir = export_dir
        self.memories_dir = export_dir / "memories"
        self.metadata_file = export_dir / "json" / "memories_history.json"

    def get_media_files(self) -> list[Path]:
        if not self.memories_dir.exists():
            return []
        all_extensions = MEDIA_EXTENSIONS["photo"] | MEDIA_EXTENSIONS["video"]
        files = []
        for ext in all_extensions:
            files.extend(self.memories_dir.rglob(f"*{ext}"))
        return sorted(files)

    def _classify_media_type(self, filepath: Path) -> str:
        suffix = filepath.suffix.lower()
        for media_type, extensions in MEDIA_EXTENSIONS.items():
            if suffix in extensions:
                return media_type
        return "photo"

    def _build_json_index(self) -> dict[str, dict]:
        """Build a lookup from lowercase UUID -> JSON entry metadata."""
        if not self.metadata_file.exists():
            return {}

        raw = json.loads(self.metadata_file.read_text(encoding="utf-8"))
        index = {}

        for entry in raw.get("Saved Media", []):
            # Try to extract UUID from the download URL's 'sid' parameter
            sid = _extract_sid(entry.get("Download Link", ""))
            if not sid:
                sid = _extract_sid(entry.get("Media Download Url", ""))
            if not sid:
                continue

            lat, lon = None, None
            if location := entry.get("Location"):
                lat, lon = _parse_location(location)

            index[sid] = {
                "timestamp": _parse_timestamp(entry.get("Date", "")),
                "media_type": "video" if entry.get("Media Type") == "Video" else "photo",
                "latitude": lat,
                "longitude": lon,
            }

        return index

    def parse_metadata(self) -> list[MediaRecord]:
        """Parse Snapchat export into MediaRecords.

        Matches files in memories/ to JSON metadata entries by UUID.
        Files without a JSON match still get ingested with filename-derived dates.
        """
        json_index = self._build_json_index()
        files = self.get_media_files()

        if not files:
            print(f"No media files found in {self.memories_dir}")
            return []

        records = []
        matched = 0
        unmatched = 0

        for filepath in files:
            file_uuid = _extract_uuid_from_filename(filepath.name)
            meta = json_index.get(file_uuid) if file_uuid else None

            if meta:
                matched += 1
                records.append(MediaRecord(
                    filepath=str(filepath),
                    source="snapchat",
                    media_type=meta["media_type"],
                    timestamp=meta["timestamp"],
                    latitude=meta["latitude"],
                    longitude=meta["longitude"],
                ))
            else:
                unmatched += 1
                # Extract date from filename as fallback
                date_match = re.match(r"(\d{4}-\d{2}-\d{2})", filepath.name)
                timestamp = f"{date_match.group(1)}T00:00:00+00:00" if date_match else None

                records.append(MediaRecord(
                    filepath=str(filepath),
                    source="snapchat",
                    media_type=self._classify_media_type(filepath),
                    timestamp=timestamp,
                ))

        print(f"Found {len(files)} media files. Matched to JSON: {matched}, Unmatched: {unmatched}")
        if json_index:
            unlinked = len(json_index) - matched
            if unlinked > 0:
                print(f"  ({unlinked} JSON entries had no matching file)")

        return records
