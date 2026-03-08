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
│   ├── api/
│   │   ├── main.py          # FastAPI app, CORS, static file serving
│   │   ├── auth.py          # single-password JWT auth
│   │   └── routes/
│   │       ├── media.py     # timeline, detail, file serving endpoints
│   │       ├── people.py    # people list + person gallery endpoints
│   │       └── search.py    # CLIP, tag, transcript search endpoints
│   ├── enrich.py            # source-agnostic enrichment pipeline
│   ├── query.py             # CLI query interface
│   └── thumbnails.py        # one-time thumbnail + video poster frame generation
│
├── web/                     # Vue 3 + Vite frontend
│   ├── src/
│   │   ├── views/
│   │   │   ├── Login.vue
│   │   │   ├── Timeline.vue
│   │   │   ├── People.vue
│   │   │   ├── Search.vue
│   │   │   └── Detail.vue
│   │   └── api.js           # fetch wrapper, attaches JWT, redirects on 401
│   └── vite.config.js       # proxies /api to FastAPI in dev
│
├── .env                     # APP_PASSWORD, SECRET_KEY — gitignored
├── .env.example             # committed, shows required vars without values
│
└── data/                    # gitignored, never committed
    ├── originals/           # write-protected after copy
    │   └── snapchat/
    ├── processed/
    │   └── thumbnails/      # {media_id}.jpg for all photos and videos
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

## Web Interface

**Stack:** FastAPI backend + Vue 3 (Vite) frontend. Mobile-first. Password-protected.

**Build phases:**
1. **Phase 0 — Prerequisites:** install `fastapi uvicorn python-jose[cryptography] python-multipart python-dotenv`, Node.js, scaffold `web/` with `npm create vite@latest web -- --template vue`
2. **Phase 1 — Thumbnails:** run `python -m src.thumbnails` once to pre-generate `data/processed/thumbnails/{id}.jpg` for all photos (Pillow) and videos (ffmpeg first frame)
3. **Phase 2 — Backend:** FastAPI with JWT auth middleware; routes for timeline, people, search, file serving
4. **Phase 3 — Frontend:** Vue Router + 5 views (Login, Timeline, People, Search, Detail); 2-col mobile grid; video play overlay on thumbnails
5. **Phase 4 — Integration:** dev uses Vite proxy (`/api → :8000`); prod builds Vue to `web/dist/` served as static files by FastAPI

**Auth:** single `APP_PASSWORD` in `.env` → JWT token (7-day expiry) stored in browser localStorage. All API routes protected. `.env` is gitignored; `.env.example` is committed.

**Access:** home network (`localhost` / `192.168.x.x`) for now. Tailscale remote access is a future drop-in with no code changes.

## Future Extensibility

**iPhone Photos:**
- Mac Photos app export preserves EXIF fully
- `osxphotos` library can export with existing face clusters and album metadata
- Approach TBD (user doesn't currently have Mac)
