"""CLI query interface for searching the memories database."""

import argparse
import sqlite3

from .db.schema import init_db
from .tagging import search_by_text


def _print_results(rows: list, fields: list[str]) -> None:
    if not rows:
        print("No results found.")
        return
    for row in rows:
        parts = [f"{f}={row[f]}" for f in fields if row[f] is not None]
        print("  " + "  |  ".join(parts))
    print(f"\n({len(rows)} result{'s' if len(rows) != 1 else ''})")


def query_by_person(conn: sqlite3.Connection, name: str) -> None:
    rows = conn.execute("""
        SELECT m.id, m.filepath, m.timestamp, m.source
        FROM media m
        JOIN face_appearances fa ON m.id = fa.media_id
        JOIN people p ON fa.person_id = p.id
        WHERE p.name LIKE ?
        ORDER BY m.timestamp DESC
    """, (f"%{name}%",)).fetchall()
    print(f"Photos with '{name}':")
    _print_results(rows, ["id", "filepath", "timestamp", "source"])


def query_by_tag(conn: sqlite3.Connection, tag: str) -> None:
    rows = conn.execute("""
        SELECT m.id, m.filepath, m.timestamp, t.tag, t.confidence
        FROM media m
        JOIN tags t ON m.id = t.media_id
        WHERE t.tag LIKE ? AND t.tag NOT LIKE 'transcription:%'
        ORDER BY t.confidence DESC
    """, (f"%{tag}%",)).fetchall()
    print(f"Media tagged with '{tag}':")
    _print_results(rows, ["id", "filepath", "timestamp", "tag", "confidence"])


def query_by_location(conn: sqlite3.Connection, place: str) -> None:
    rows = conn.execute("""
        SELECT m.id, m.filepath, m.timestamp, l.place_name
        FROM media m
        JOIN locations l ON m.id = l.media_id
        WHERE l.place_name LIKE ?
        ORDER BY m.timestamp DESC
    """, (f"%{place}%",)).fetchall()
    print(f"Media near '{place}':")
    _print_results(rows, ["id", "filepath", "timestamp", "place_name"])


def query_by_date(conn: sqlite3.Connection, date: str) -> None:
    rows = conn.execute("""
        SELECT m.id, m.filepath, m.timestamp, m.source, m.media_type
        FROM media m
        WHERE m.timestamp LIKE ?
        ORDER BY m.timestamp
    """, (f"{date}%",)).fetchall()
    print(f"Media from '{date}':")
    _print_results(rows, ["id", "filepath", "timestamp", "source", "media_type"])


def query_transcriptions(conn: sqlite3.Connection, text: str) -> None:
    rows = conn.execute("""
        SELECT m.id, m.filepath, m.timestamp, t.tag
        FROM media m
        JOIN tags t ON m.id = t.media_id
        WHERE t.tag LIKE ?
        ORDER BY m.timestamp DESC
    """, (f"transcription:%{text}%",)).fetchall()
    print(f"Videos mentioning '{text}':")
    if not rows:
        print("No results found.")
        return
    for row in rows:
        transcript = row["tag"].removeprefix("transcription:")
        preview = transcript[:100] + "..." if len(transcript) > 100 else transcript
        print(f"  id={row['id']}  |  {row['filepath']}  |  \"{preview}\"")
    print(f"\n({len(rows)} result{'s' if len(rows) != 1 else ''})")


def query_clip_search(conn: sqlite3.Connection, query: str, top_k: int) -> None:
    print(f"Searching for '{query}' (top {top_k})...")
    results = search_by_text(conn, query, top_k=top_k)
    if not results:
        print("No results found.")
        return
    for r in results:
        print(f"  score={r['score']}  |  id={r['media_id']}  |  {r['filepath']}")
    print(f"\n({len(results)} result{'s' if len(results) != 1 else ''})")


def query_stats(conn: sqlite3.Connection) -> None:
    total = conn.execute("SELECT COUNT(*) FROM media").fetchone()[0]
    photos = conn.execute("SELECT COUNT(*) FROM media WHERE media_type = 'photo'").fetchone()[0]
    videos = conn.execute("SELECT COUNT(*) FROM media WHERE media_type = 'video'").fetchone()[0]
    people = conn.execute("SELECT COUNT(*) FROM people").fetchone()[0]
    tagged = conn.execute("SELECT COUNT(DISTINCT media_id) FROM tags WHERE tag NOT LIKE 'transcription:%'").fetchone()[0]
    transcribed = conn.execute("SELECT COUNT(DISTINCT media_id) FROM tags WHERE tag LIKE 'transcription:%' AND tag != 'transcription:'").fetchone()[0]
    geocoded = conn.execute("SELECT COUNT(*) FROM locations").fetchone()[0]
    sources = conn.execute("SELECT source, COUNT(*) as cnt FROM media GROUP BY source").fetchall()

    print("=== Database Stats ===")
    print(f"  Total media:    {total} ({photos} photos, {videos} videos)")
    print(f"  People:         {people}")
    print(f"  Tagged:         {tagged}")
    print(f"  Transcribed:    {transcribed}")
    print(f"  Geocoded:       {geocoded}")
    if sources:
        print(f"  Sources:        {', '.join(f'{s['source']}({s['cnt']})' for s in sources)}")


def main():
    parser = argparse.ArgumentParser(description="Query the memories database.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # stats
    subparsers.add_parser("stats", help="Show database statistics")

    # person
    p = subparsers.add_parser("person", help="Find media by person name")
    p.add_argument("name", help="Person name (partial match)")

    # tag
    p = subparsers.add_parser("tag", help="Find media by tag")
    p.add_argument("tag", help="Tag to search for (partial match)")

    # location
    p = subparsers.add_parser("location", help="Find media by location")
    p.add_argument("place", help="Place name (partial match)")

    # date
    p = subparsers.add_parser("date", help="Find media by date")
    p.add_argument("date", help="Date prefix, e.g. '2023-01-15' or '2023-01'")

    # transcript
    p = subparsers.add_parser("transcript", help="Search video transcriptions")
    p.add_argument("text", help="Text to search for in transcriptions")

    # search (CLIP natural language)
    p = subparsers.add_parser("search", help="Natural language image search via CLIP")
    p.add_argument("query", help="Natural language query, e.g. 'birthday cake'")
    p.add_argument("-n", "--top", type=int, default=10, help="Number of results (default: 10)")

    args = parser.parse_args()

    conn = init_db()
    try:
        if args.command == "stats":
            query_stats(conn)
        elif args.command == "person":
            query_by_person(conn, args.name)
        elif args.command == "tag":
            query_by_tag(conn, args.tag)
        elif args.command == "location":
            query_by_location(conn, args.place)
        elif args.command == "date":
            query_by_date(conn, args.date)
        elif args.command == "transcript":
            query_transcriptions(conn, args.text)
        elif args.command == "search":
            query_clip_search(conn, args.query, args.top)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
