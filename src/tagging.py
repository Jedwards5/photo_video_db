"""Semantic tagging via CLIP — zero-shot image classification and embedding storage."""

import sqlite3
from pathlib import Path

import numpy as np
import open_clip
import torch
from PIL import Image

from .db.schema import init_db

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CLIP_EMBEDDINGS_DIR = DATA_DIR / "db" / "clip_embeddings"

# Model choice: ViT-B/32 is a good balance of speed and quality for personal photos.
# On an RTX 5070 Ti this processes hundreds of images per minute.
CLIP_MODEL = "ViT-B-32"
CLIP_PRETRAINED = "laion2b_s34b_b79k"

# Predefined tags for zero-shot classification.
# These are phrased as "a photo of {tag}" internally by CLIP.
DEFAULT_TAGS = [
    # People & social
    "a selfie", "a group photo", "a couple", "a baby", "a child",
    # Places & scenes
    "a beach", "a mountain", "a city skyline", "a forest", "a park",
    "a lake or river", "a sunset or sunrise", "a snowy scene",
    # Events
    "a birthday party", "a wedding", "a graduation", "a concert",
    "a holiday celebration", "a sporting event",
    # Food & drink
    "food on a plate", "a restaurant meal", "a drink or cocktail",
    # Animals
    "a dog", "a cat", "a pet",
    # Activities
    "people swimming", "people hiking", "people dancing",
    "people playing sports", "people cooking",
    # Objects & misc
    "a car", "a building", "flowers", "a screenshot",
    "artwork or a painting", "a document or text",
    # Mood / quality
    "a night scene", "an indoor scene", "an outdoor scene",
    "a close-up or macro shot", "a landscape photo",
]

# Minimum confidence to store a tag
TAG_THRESHOLD = 0.15
# Maximum tags per image
MAX_TAGS_PER_IMAGE = 5


def _load_clip(device: torch.device):
    model, _, preprocess = open_clip.create_model_and_transforms(
        CLIP_MODEL, pretrained=CLIP_PRETRAINED, device=device,
    )
    tokenizer = open_clip.get_tokenizer(CLIP_MODEL)
    return model, preprocess, tokenizer


def _compute_text_features(model, tokenizer, tags: list[str], device: torch.device):
    tokens = tokenizer(tags).to(device)
    with torch.no_grad():
        text_features = model.encode_text(tokens)
        text_features /= text_features.norm(dim=-1, keepdim=True)
    return text_features


def tag_photos(conn: sqlite3.Connection, tags: list[str] | None = None) -> None:
    """Run zero-shot CLIP classification on all untagged photos."""
    if tags is None:
        tags = DEFAULT_TAGS

    CLIP_EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    print(f"Loading CLIP model ({CLIP_MODEL})...")

    model, preprocess, tokenizer = _load_clip(device)
    text_features = _compute_text_features(model, tokenizer, tags, device)

    # Find photos that haven't been tagged yet
    rows = conn.execute("""
        SELECT m.id, m.filepath FROM media m
        WHERE m.media_type = 'photo'
          AND m.id NOT IN (SELECT DISTINCT media_id FROM tags)
    """).fetchall()

    if not rows:
        print("No untagged photos found.")
        return

    print(f"Tagging {len(rows)} photos with {len(tags)} candidate labels...")

    tagged = 0
    failed = 0

    for i, row in enumerate(rows):
        media_id = row["id"]
        filepath = row["filepath"]

        try:
            img = preprocess(Image.open(filepath).convert("RGB")).unsqueeze(0).to(device)
        except Exception as e:
            print(f"  [{i+1}/{len(rows)}] media_id={media_id}: failed to open — {e}")
            failed += 1
            continue

        with torch.no_grad():
            image_features = model.encode_image(img)
            image_features /= image_features.norm(dim=-1, keepdim=True)

            # Save raw CLIP embedding for later natural language search
            np.save(
                CLIP_EMBEDDINGS_DIR / f"{media_id}.npy",
                image_features.cpu().numpy(),
            )

            # Compute similarity scores against all tags
            similarities = (image_features @ text_features.T).squeeze(0).cpu().numpy()

        # Store top tags above threshold
        top_indices = similarities.argsort()[::-1][:MAX_TAGS_PER_IMAGE]
        for idx in top_indices:
            score = float(similarities[idx])
            if score < TAG_THRESHOLD:
                break
            # Clean up tag text: remove "a photo of" prefix style
            tag_name = tags[idx].removeprefix("a ").removeprefix("an ").removeprefix("people ")
            conn.execute(
                "INSERT OR IGNORE INTO tags (media_id, tag, confidence) VALUES (?, ?, ?)",
                (media_id, tag_name, round(score, 4)),
            )

        tagged += 1
        if (i + 1) % 100 == 0 or i == len(rows) - 1:
            print(f"  [{i+1}/{len(rows)}] processed")

    conn.commit()
    print(f"\nTagging complete. Tagged: {tagged}, Failed: {failed}")


def search_by_text(conn: sqlite3.Connection, query: str, top_k: int = 10) -> list[dict]:
    """Search photos by natural language using stored CLIP embeddings.

    Returns a list of dicts with 'media_id', 'filepath', 'score'.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, _, _ = _load_clip(device)
    tokenizer = open_clip.get_tokenizer(CLIP_MODEL)

    # Encode the query text
    tokens = tokenizer([query]).to(device)
    with torch.no_grad():
        text_features = model.encode_text(tokens)
        text_features /= text_features.norm(dim=-1, keepdim=True)
        text_features = text_features.cpu().numpy()

    # Score against all stored image embeddings
    emb_files = sorted(CLIP_EMBEDDINGS_DIR.glob("*.npy"))
    if not emb_files:
        print("No CLIP embeddings found. Run tagging first.")
        return []

    scores = []
    for emb_file in emb_files:
        media_id = int(emb_file.stem)
        image_features = np.load(emb_file)
        similarity = float(image_features @ text_features.T)
        scores.append((media_id, similarity))

    scores.sort(key=lambda x: x[1], reverse=True)
    top_results = scores[:top_k]

    results = []
    for media_id, score in top_results:
        row = conn.execute(
            "SELECT filepath FROM media WHERE id = ?", (media_id,)
        ).fetchone()
        if row:
            results.append({
                "media_id": media_id,
                "filepath": row["filepath"],
                "score": round(score, 4),
            })

    return results
