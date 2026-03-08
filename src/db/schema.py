"""SQLite schema creation for the memories database."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "db" / "memories.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            media_type TEXT NOT NULL CHECK(media_type IN ('photo', 'video')),
            timestamp TEXT,
            latitude REAL,
            longitude REAL,
            duration_seconds REAL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS face_appearances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_id INTEGER NOT NULL REFERENCES media(id),
            person_id INTEGER NOT NULL REFERENCES people(id),
            confidence REAL,
            UNIQUE(media_id, person_id)
        );

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_id INTEGER NOT NULL REFERENCES media(id),
            tag TEXT NOT NULL,
            confidence REAL,
            UNIQUE(media_id, tag)
        );

        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_id INTEGER NOT NULL UNIQUE REFERENCES media(id),
            place_name TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_media_source ON media(source);
        CREATE INDEX IF NOT EXISTS idx_media_timestamp ON media(timestamp);
        CREATE INDEX IF NOT EXISTS idx_media_type ON media(media_type);
        CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
    """)


def init_db() -> sqlite3.Connection:
    conn = get_connection()
    create_tables(conn)
    return conn
