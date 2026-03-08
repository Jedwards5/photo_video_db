"""Media endpoints: timeline, detail, file serving, thumbnails."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ...db.schema import init_db
from ..auth import verify_token

router = APIRouter()

THUMB_DIR = Path("data/processed/thumbnails")
PAGE_SIZE = 50


@router.get("/api/timeline")
def get_timeline(page: int = 1, _token: str = Depends(verify_token)):
    conn = init_db()
    try:
        offset = (page - 1) * PAGE_SIZE
        rows = conn.execute("""
            SELECT id, filepath, media_type, timestamp, latitude, longitude
            FROM media
            WHERE timestamp IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """, (PAGE_SIZE, offset)).fetchall()

        total = conn.execute(
            "SELECT COUNT(*) FROM media WHERE timestamp IS NOT NULL"
        ).fetchone()[0]

        items = []
        for row in rows:
            thumb_path = THUMB_DIR / f"{row['id']}.jpg"
            items.append({
                "id": row["id"],
                "media_type": row["media_type"],
                "timestamp": row["timestamp"],
                "has_thumbnail": thumb_path.exists(),
            })

        return {
            "items": items,
            "page": page,
            "total": total,
            "pages": (total + PAGE_SIZE - 1) // PAGE_SIZE,
        }
    finally:
        conn.close()


@router.get("/api/media/{media_id}")
def get_media_detail(media_id: int, _token: str = Depends(verify_token)):
    conn = init_db()
    try:
        row = conn.execute(
            "SELECT * FROM media WHERE id = ?", (media_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Not found")

        tags = conn.execute(
            "SELECT tag, confidence FROM tags WHERE media_id = ? AND tag NOT LIKE 'transcription:%' ORDER BY confidence DESC",
            (media_id,)
        ).fetchall()

        transcript_row = conn.execute(
            "SELECT tag FROM tags WHERE media_id = ? AND tag LIKE 'transcription:%'",
            (media_id,)
        ).fetchone()

        people = conn.execute("""
            SELECT p.id, p.name FROM people p
            JOIN face_appearances fa ON p.id = fa.person_id
            WHERE fa.media_id = ?
        """, (media_id,)).fetchall()

        location = conn.execute(
            "SELECT place_name FROM locations WHERE media_id = ?", (media_id,)
        ).fetchone()

        # prev/next by timestamp
        prev_row = conn.execute("""
            SELECT id FROM media WHERE timestamp > ? AND timestamp IS NOT NULL
            ORDER BY timestamp ASC LIMIT 1
        """, (row["timestamp"],)).fetchone()
        next_row = conn.execute("""
            SELECT id FROM media WHERE timestamp < ? AND timestamp IS NOT NULL
            ORDER BY timestamp DESC LIMIT 1
        """, (row["timestamp"],)).fetchone()

        return {
            "id": row["id"],
            "filepath": row["filepath"],
            "media_type": row["media_type"],
            "timestamp": row["timestamp"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "source": row["source"],
            "tags": [{"tag": t["tag"], "confidence": round(t["confidence"], 3)} for t in tags],
            "transcript": transcript_row["tag"].removeprefix("transcription:") if transcript_row else None,
            "people": [{"id": p["id"], "name": p["name"]} for p in people],
            "location": location["place_name"] if location else None,
            "prev_id": prev_row["id"] if prev_row else None,
            "next_id": next_row["id"] if next_row else None,
        }
    finally:
        conn.close()


@router.get("/api/thumbnails/{media_id}")
def get_thumbnail(media_id: int, _token: str = Depends(verify_token)):
    thumb = THUMB_DIR / f"{media_id}.jpg"
    if not thumb.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(thumb, media_type="image/jpeg")


@router.get("/api/files/{media_id}")
def get_file(media_id: int, _token: str = Depends(verify_token)):
    conn = init_db()
    try:
        row = conn.execute(
            "SELECT filepath, media_type FROM media WHERE id = ?", (media_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        path = Path(row["filepath"])
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        ext = path.suffix.lower()
        mime = {
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }.get(ext, "application/octet-stream")
        return FileResponse(path, media_type=mime)
    finally:
        conn.close()
