"""People endpoints: list clusters and browse by person."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from ...db.schema import init_db
from ..auth import verify_token

router = APIRouter()

THUMB_DIR = Path("data/processed/thumbnails")
PAGE_SIZE = 50


@router.get("/api/people")
def list_people(_token: str = Depends(verify_token)):
    conn = init_db()
    try:
        rows = conn.execute("""
            SELECT p.id, p.name, COUNT(fa.media_id) as count,
                   MIN(fa.media_id) as sample_id
            FROM people p
            JOIN face_appearances fa ON p.id = fa.person_id
            GROUP BY p.id
            ORDER BY count DESC
        """).fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "count": r["count"],
                "sample_id": r["sample_id"],
            }
            for r in rows
        ]
    finally:
        conn.close()


@router.get("/api/people/{person_id}/media")
def get_person_media(person_id: int, page: int = 1, _token: str = Depends(verify_token)):
    conn = init_db()
    try:
        person = conn.execute(
            "SELECT id, name FROM people WHERE id = ?", (person_id,)
        ).fetchone()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        offset = (page - 1) * PAGE_SIZE
        rows = conn.execute("""
            SELECT m.id, m.media_type, m.timestamp
            FROM media m
            JOIN face_appearances fa ON m.id = fa.media_id
            WHERE fa.person_id = ?
            ORDER BY m.timestamp DESC
            LIMIT ? OFFSET ?
        """, (person_id, PAGE_SIZE, offset)).fetchall()

        total = conn.execute(
            "SELECT COUNT(*) FROM face_appearances WHERE person_id = ?", (person_id,)
        ).fetchone()[0]

        items = [
            {
                "id": r["id"],
                "media_type": r["media_type"],
                "timestamp": r["timestamp"],
                "has_thumbnail": (THUMB_DIR / f"{r['id']}.jpg").exists(),
            }
            for r in rows
        ]
        return {
            "person": {"id": person["id"], "name": person["name"]},
            "items": items,
            "page": page,
            "total": total,
            "pages": (total + PAGE_SIZE - 1) // PAGE_SIZE,
        }
    finally:
        conn.close()
