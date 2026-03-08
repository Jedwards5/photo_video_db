"""Face detection, embedding, clustering, and labeling."""

import sqlite3
from pathlib import Path

import numpy as np
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image
from sklearn.cluster import DBSCAN

from .db.schema import init_db

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EMBEDDINGS_DIR = DATA_DIR / "db" / "face_embeddings"


def _get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def detect_and_embed(conn: sqlite3.Connection) -> None:
    """Detect faces in all photos and store embeddings.

    Skips media that already has embeddings saved to disk.
    Only processes photos (not videos).
    """
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    device = _get_device()
    print(f"Using device: {device}")

    mtcnn = MTCNN(
        keep_all=True,
        device=device,
        min_face_size=40,
        thresholds=[0.6, 0.7, 0.7],
    )
    resnet = InceptionResnetV1(pretrained="vggface2").eval().to(device)

    rows = conn.execute(
        "SELECT id, filepath FROM media WHERE media_type = 'photo'"
    ).fetchall()

    if not rows:
        print("No photos in database to process.")
        return

    processed = 0
    skipped = 0
    total_faces = 0

    for i, row in enumerate(rows):
        media_id = row["id"]
        filepath = row["filepath"]
        emb_path = EMBEDDINGS_DIR / f"{media_id}.npy"

        if emb_path.exists():
            skipped += 1
            continue

        try:
            img = Image.open(filepath).convert("RGB")
        except Exception as e:
            print(f"  [{i+1}/{len(rows)}] media_id={media_id}: failed to open — {e}")
            np.save(emb_path, np.empty((0, 512)))
            continue

        faces = mtcnn(img)
        if faces is None:
            np.save(emb_path, np.empty((0, 512)))
            processed += 1
            continue

        if faces.dim() == 3:
            faces = faces.unsqueeze(0)

        with torch.no_grad():
            embeddings = resnet(faces.to(device)).cpu().numpy()

        np.save(emb_path, embeddings)
        total_faces += len(embeddings)
        processed += 1

        if (i + 1) % 100 == 0 or i == len(rows) - 1:
            print(f"  [{i+1}/{len(rows)}] processed, {total_faces} faces found so far")

    print(f"\nFace detection complete. Processed: {processed}, Skipped: {skipped}, Faces found: {total_faces}")


def cluster_faces(conn: sqlite3.Connection, eps: float = 0.7, min_samples: int = 3) -> None:
    """Cluster face embeddings using DBSCAN and populate face_appearances.

    Args:
        eps: Maximum distance between two samples in a cluster. Lower = stricter matching.
        min_samples: Minimum faces to form a cluster (person must appear at least this many times).
    """
    emb_files = sorted(EMBEDDINGS_DIR.glob("*.npy"))
    if not emb_files:
        print("No embeddings found. Run face detection first.")
        return

    # Load all embeddings, tracking which media_id and face index they belong to
    all_embeddings = []
    face_index = []  # list of (media_id, face_idx_within_image)

    for emb_file in emb_files:
        media_id = int(emb_file.stem)
        embeddings = np.load(emb_file)
        if embeddings.shape[0] == 0:
            continue
        for idx in range(embeddings.shape[0]):
            all_embeddings.append(embeddings[idx])
            face_index.append((media_id, idx))

    if not all_embeddings:
        print("No face embeddings to cluster.")
        return

    all_embeddings = np.array(all_embeddings)
    print(f"Clustering {len(all_embeddings)} face embeddings (eps={eps}, min_samples={min_samples})...")

    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="euclidean").fit(all_embeddings)
    labels = clustering.labels_

    n_clusters = len(set(labels) - {-1})
    n_noise = (labels == -1).sum()
    print(f"Found {n_clusters} clusters, {n_noise} unclustered faces")

    # Clear previous clustering results
    conn.execute("DELETE FROM face_appearances")
    conn.execute("DELETE FROM people")
    conn.commit()

    # Create a person entry for each cluster
    cluster_to_person = {}
    for cluster_id in sorted(set(labels) - {-1}):
        cursor = conn.execute(
            "INSERT INTO people (name) VALUES (?)",
            (f"Person {cluster_id + 1}",),
        )
        cluster_to_person[cluster_id] = cursor.lastrowid

    # Insert face appearances
    for (media_id, _face_idx), label in zip(face_index, labels):
        if label == -1:
            continue
        person_id = cluster_to_person[label]
        conn.execute(
            "INSERT OR IGNORE INTO face_appearances (media_id, person_id) VALUES (?, ?)",
            (media_id, person_id),
        )

    conn.commit()

    # Print summary
    for cluster_id, person_id in cluster_to_person.items():
        count = conn.execute(
            "SELECT COUNT(*) FROM face_appearances WHERE person_id = ?",
            (person_id,),
        ).fetchone()[0]
        print(f"  Person {cluster_id + 1}: appears in {count} photos")


def label_faces(conn: sqlite3.Connection) -> None:
    """Interactive CLI to name face clusters."""
    people = conn.execute(
        """SELECT p.id, p.name, COUNT(fa.id) as count
           FROM people p
           JOIN face_appearances fa ON p.id = fa.person_id
           GROUP BY p.id
           ORDER BY count DESC"""
    ).fetchall()

    if not people:
        print("No face clusters found. Run face detection and clustering first.")
        return

    print(f"\n{len(people)} face clusters found. Enter a name for each (or press Enter to skip):\n")

    for person in people:
        person_id, current_name, count = person["id"], person["name"], person["count"]

        # Show sample photos for this person
        samples = conn.execute(
            """SELECT m.filepath FROM media m
               JOIN face_appearances fa ON m.id = fa.media_id
               WHERE fa.person_id = ?
               LIMIT 5""",
            (person_id,),
        ).fetchall()

        print(f"  [{current_name}] — appears in {count} photos")
        print(f"  Sample photos: {', '.join(Path(s['filepath']).name for s in samples)}")

        new_name = input(f"  Name for {current_name} (Enter to skip): ").strip()
        if new_name:
            conn.execute("UPDATE people SET name = ? WHERE id = ?", (new_name, person_id))
            print(f"  -> Renamed to '{new_name}'")
        print()

    conn.commit()
    print("Labeling complete.")
