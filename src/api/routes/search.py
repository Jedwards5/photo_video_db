"""Search endpoints: CLIP natural language, tag, and transcript search."""

from pathlib import Path

from fastapi import APIRouter, Depends

from ...db.schema import init_db
from ...tagging import search_by_text
from ..auth import verify_token

router = APIRouter()

THUMB_DIR = Path("data/processed/thumbnails")


@router.get("/api/search")
def search(q: str, mode: str = "clip", top: int = 30, _token: str = Depends(verify_token)):
    """
    Search media. mode = "clip" | "tag" | "transcript"
    """
    conn = init_db()
    try:
        if mode == "clip":
            results = search_by_text(conn, q, top_k=top)
            items = []
            for r in results:
                row = conn.execute(
                    "SELECT id, media_type, timestamp FROM media WHERE id = ?",
                    (r["media_id"],)
                ).fetchone()
                if row:
                    items.append({
                        "id": row["id"],
                        "media_type": row["media_type"],
                        "timestamp": row["timestamp"],
                        "score": round(r["score"], 4),
                        "has_thumbnail": (THUMB_DIR / f"{row['id']}.jpg").exists(),
                    })
            return {"mode": "clip", "query": q, "items": items}

        elif mode == "tag":
            rows = conn.execute("""
                SELECT m.id, m.media_type, m.timestamp, t.confidence
                FROM media m
                JOIN tags t ON m.id = t.media_id
                WHERE t.tag LIKE ? AND t.tag NOT LIKE 'transcription:%'
                ORDER BY t.confidence DESC
                LIMIT ?
            """, (f"%{q}%", top)).fetchall()
            items = [
                {
                    "id": r["id"],
                    "media_type": r["media_type"],
                    "timestamp": r["timestamp"],
                    "score": round(r["confidence"], 4),
                    "has_thumbnail": (THUMB_DIR / f"{r['id']}.jpg").exists(),
                }
                for r in rows
            ]
            return {"mode": "tag", "query": q, "items": items}

        elif mode == "transcript":
            rows = conn.execute("""
                SELECT m.id, m.media_type, m.timestamp, t.tag
                FROM media m
                JOIN tags t ON m.id = t.media_id
                WHERE t.tag LIKE ?
                ORDER BY m.timestamp DESC
                LIMIT ?
            """, (f"transcription:%{q}%", top)).fetchall()
            items = [
                {
                    "id": r["id"],
                    "media_type": r["media_type"],
                    "timestamp": r["timestamp"],
                    "snippet": r["tag"].removeprefix("transcription:")[:120],
                    "has_thumbnail": (THUMB_DIR / f"{r['id']}.jpg").exists(),
                }
                for r in rows
            ]
            return {"mode": "transcript", "query": q, "items": items}

        return {"mode": mode, "query": q, "items": []}
    finally:
        conn.close()
