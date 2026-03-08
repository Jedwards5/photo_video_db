# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal Memories Archive is a local-first, privacy-preserving personal media archive system. It ingests Snapchat memory exports (and eventually other sources like iPhone photos), enriches them with AI-generated metadata using local-only models, and stores everything in a queryable SQLite database.

**Critical Design Principles:**
- **Local-first, no cloud** — All processing happens locally. No images or metadata sent to external APIs.
- **Originals are sacred** — Source files are never modified. All enrichment lives in SQLite.
- **Source-agnostic architecture** — Designed to support multiple data sources (Snapchat first, iPhone/Instagram later).

## Architecture

### Directory Structure

```
memories/
├── src/
│   ├── sources/
│   │   ├── base.py          # shared interface all source adapters implement
│   │   ├── snapchat.py      # Snapchat-specific ingest logic
│   │   └── iphone.py        # iPhone-specific ingest logic (future)
│   ├── enrich.py            # source-agnostic enrichment pipeline
│   └── query.py             # CLI query interface
│
└── data/                    # gitignored, never committed
    ├── originals/           # write-protected after copy (chmod -R 444)
    │   ├── snapchat/        # memories_history.json, photos/, videos/
    │   └── iphone/
    ├── processed/           # working copies for resizing, transcoding
    └── db/
        ├── memories.db      # single unified SQLite database
        └── face_embeddings/ # face embedding vectors
```

### Source Adapter Pattern

Each data source implements a common interface in `src/sources/base.py`:
- `parse_metadata()` — reads source-specific export format, returns normalized records
- `get_media_files()` — returns list of media file paths
- `normalize_record()` — maps source fields to unified schema

Adding new sources requires only implementing this interface without touching enrichment or query logic.

### Database Schema

SQLite database (`data/db/memories.db`) with source-agnostic design:
- `media` — one row per photo/video (filepath, timestamp, source, media type)
- `people` — named face clusters
- `face_appearances` — join table linking media to people
- `tags` — semantic/scene tags from CLIP
- `locations` — reverse-geocoded place names

Every record carries a `source` field for filtering.

## Enrichment Pipeline (implementation order)

1. **Ingest & normalize** — parse `memories_history.json`, populate `media` table
2. **Reverse geocoding** — GPS → place names via `geopy` + Nominatim (OpenStreetMap)
3. **Face detection & clustering** — detect, embed, cluster faces; user names clusters
4. **Semantic tagging** — `open-clip` or HuggingFace `transformers` for scene/object tags
5. **Video transcription** — `openai-whisper` locally for searchable audio text
6. **Query interface** — CLI query layer built after data pipeline is complete

## Local-Only Model Stack

All models run offline with no API keys:
- **Semantic search:** `open-clip` or HuggingFace `transformers` (CLIP)
- **Face detection:** `face_recognition` (dlib-based)
- **Reverse geocoding:** `geopy` + Nominatim (network requests to OSM only)
- **Video transcription:** `openai-whisper` (local execution)
- **Metadata store:** `sqlite3` (stdlib)

## Security & Privacy Requirements

- `data/` directory must be excluded from cloud sync (iCloud, Google Drive, Dropbox)
- `data/originals/` must be read-only after initial copy
- `memories.db` is as sensitive as the photos themselves
- Never use cloud vision APIs
- No external API keys required or used

## Future Extensibility

**iPhone Photos:**
- Mac Photos app export preserves EXIF fully
- `osxphotos` library can export with existing face clusters and album metadata
- Approach TBD (user doesn't currently have Mac)

**Web UI:**
- CLI architecture designed to translate cleanly to Flask/FastAPI backend
- Access via same-network (192.168.x.x) or Tailscale VPN for remote access
