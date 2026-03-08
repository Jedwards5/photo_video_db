"""Video transcription via Whisper — local speech-to-text for searchable audio."""

import shutil
import sqlite3
from pathlib import Path

import torch
import whisper

from .db.schema import init_db

# Whisper model size: "base" is a good default (fast, reasonable accuracy).
# Options: tiny, base, small, medium, large
# Larger models are more accurate but slower. "small" is a good upgrade if needed.
WHISPER_MODEL = "base"


def _check_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def transcribe_videos(conn: sqlite3.Connection, model_size: str | None = None) -> None:
    """Transcribe audio from all videos that don't yet have a transcription."""
    if not _check_ffmpeg():
        print("ERROR: ffmpeg is not installed or not in PATH.")
        print("Install it with: winget install ffmpeg")
        print("Then restart your terminal and try again.")
        return

    if model_size is None:
        model_size = WHISPER_MODEL

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    # Find videos without transcriptions
    # Transcriptions are stored in the tags table with tag = 'transcription:...'
    rows = conn.execute("""
        SELECT m.id, m.filepath FROM media m
        WHERE m.media_type = 'video'
          AND m.id NOT IN (
              SELECT media_id FROM tags WHERE tag LIKE 'transcription:%'
          )
    """).fetchall()

    if not rows:
        print("No untranscribed videos found.")
        return

    print(f"Loading Whisper model ({model_size})...")
    model = whisper.load_model(model_size, device=device)

    print(f"Transcribing {len(rows)} videos...")
    transcribed = 0
    failed = 0
    silent = 0

    for i, row in enumerate(rows):
        media_id = row["id"]
        filepath = row["filepath"]

        if not Path(filepath).exists():
            print(f"  [{i+1}/{len(rows)}] media_id={media_id}: file not found, skipping")
            failed += 1
            continue

        try:
            result = model.transcribe(filepath, language="en")
            text = result["text"].strip()
        except Exception as e:
            print(f"  [{i+1}/{len(rows)}] media_id={media_id}: transcription failed — {e}")
            failed += 1
            continue

        if text:
            conn.execute(
                "INSERT OR IGNORE INTO tags (media_id, tag, confidence) VALUES (?, ?, ?)",
                (media_id, f"transcription:{text}", 1.0),
            )
            transcribed += 1
            preview = text[:80] + "..." if len(text) > 80 else text
            print(f"  [{i+1}/{len(rows)}] media_id={media_id}: \"{preview}\"")
        else:
            # Store empty marker so we don't re-process silent videos
            conn.execute(
                "INSERT OR IGNORE INTO tags (media_id, tag, confidence) VALUES (?, ?, ?)",
                (media_id, "transcription:", 0.0),
            )
            silent += 1
            print(f"  [{i+1}/{len(rows)}] media_id={media_id}: no speech detected")

    conn.commit()
    print(f"\nTranscription complete. Transcribed: {transcribed}, Silent: {silent}, Failed: {failed}")
