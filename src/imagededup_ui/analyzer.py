"""Image analysis and duplicate grouping using imagededup.

Wraps the imagededup library to encode images, find duplicates, normalise
similarity scores, and build connected-component groups for the web UI.
"""

import logging
import os
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

HASH_METHODS: tuple[str, ...] = ("phash", "dhash", "ahash", "whash")

METHOD_CLASSES: dict[str, type] = {}  # populated lazily to avoid import cost

_METHOD_CLASSES_LOADED = False


def _ensure_method_classes() -> None:
    """Lazily import imagededup method classes on first use."""
    global _METHOD_CLASSES_LOADED  # noqa: PLW0603
    if _METHOD_CLASSES_LOADED:
        return
    from imagededup.methods import CNN, AHash, DHash, PHash, WHash

    METHOD_CLASSES.update(
        {
            "phash": PHash,
            "dhash": DHash,
            "ahash": AHash,
            "whash": WHash,
            "cnn": CNN,
        }
    )
    _METHOD_CLASSES_LOADED = True


def encode(image_dir: Path, method: str) -> dict:
    """Encode all images in a directory using the specified method.

    Args:
        image_dir: Path to the directory containing images.
        method: Deduplication method (phash, dhash, ahash, whash, cnn).

    Returns:
        Encoding map from imagededup (filename → encoding).

    Raises:
        ValueError: If method is not recognized.
    """
    _ensure_method_classes()
    if method not in METHOD_CLASSES:
        raise ValueError(
            f"Unknown method '{method}', expected one of: {sorted(METHOD_CLASSES)}"
        )

    encoder = METHOD_CLASSES[method]()
    return encoder.encode_images(image_dir=str(image_dir), recursive=True)


def find_duplicates(encodings: dict, method: str, threshold: float) -> dict:
    """Find duplicate images from pre-computed encodings.

    Args:
        encodings: Encoding map from :func:`encode`.
        method: Deduplication method name.
        threshold: Similarity threshold (interpretation varies by method).

    Returns:
        Adjacency dict mapping each filename to a list of
        (duplicate_filename, score) tuples.

    Raises:
        ValueError: If method is not recognized.
    """
    _ensure_method_classes()
    if method not in METHOD_CLASSES:
        raise ValueError(
            f"Unknown method '{method}', expected one of: {sorted(METHOD_CLASSES)}"
        )

    encoder = METHOD_CLASSES[method]()

    if method in HASH_METHODS:
        return encoder.find_duplicates(
            encoding_map=encodings,
            max_distance_threshold=int(threshold),
            scores=True,
        )
    # CNN method
    return encoder.find_duplicates(
        encoding_map=encodings,
        min_similarity_threshold=threshold,
        scores=True,
    )


def normalize_score(raw_score: float, method: str) -> float:
    """Normalize a raw similarity score to a 0-100% scale.

    Args:
        raw_score: Raw score from imagededup.
            For hashing methods this is a Hamming distance (0-64).
            For CNN this is a cosine similarity (-1.0 to 1.0).
        method: Deduplication method name.

    Returns:
        Normalized similarity percentage (0-100).
    """
    if method in HASH_METHODS:
        return (64 - raw_score) / 64 * 100
    # CNN: cosine similarity
    return (raw_score + 1) / 2 * 100


def get_image_metadata(image_dir: Path, rel_path: str) -> dict:
    """Return file size and dimensions for an image.

    Args:
        image_dir: Base directory containing images.
        rel_path: Path to the image relative to image_dir.

    Returns:
        Dict with keys ``size_bytes``, ``width``, ``height``.
        Values default to 0 if the image cannot be read.
    """
    full_path = image_dir / rel_path
    metadata: dict = {"size_bytes": 0, "width": 0, "height": 0}

    try:
        stat = os.stat(full_path)
        metadata["size_bytes"] = stat.st_size
    except OSError as exc:
        logger.warning("Cannot stat file %s: %s", rel_path, exc)
        return metadata

    try:
        with Image.open(full_path) as img:
            metadata["width"], metadata["height"] = img.size
    except Exception as exc:  # noqa: BLE001
        logger.warning("Cannot read image dimensions for %s: %s", rel_path, exc)

    return metadata


def build_groups(
    duplicates: dict[str, list[tuple[str, float]]],
    method: str,
    image_dir: Path,
) -> list[dict]:
    """Convert an adjacency dict to connected-component groups.

    Uses Union-Find to identify connected components from the symmetric
    adjacency list returned by imagededup.  Only images with at least one
    duplicate are included.

    Args:
        duplicates: Adjacency dict mapping each filename to a list of
            (duplicate_filename, score) tuples.
        method: Deduplication method name (used for score normalisation).
        image_dir: Base directory containing images (used for metadata).

    Returns:
        List of group dicts sorted by size (largest first), then
        alphabetically by first filename.  Each group contains an ``id``
        and an ``images`` list.
    """
    # --- Union-Find ----------------------------------------------------------
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Initialise parent for every node that participates in at least one edge
    for img, neighbours in duplicates.items():
        if neighbours:
            parent.setdefault(img, img)
            for neighbour, _score in neighbours:
                parent.setdefault(neighbour, neighbour)
                union(img, neighbour)

    # --- Collect components --------------------------------------------------
    components: dict[str, set[str]] = {}
    for node in parent:
        root = find(node)
        components.setdefault(root, set()).add(node)

    # --- Build score lookup (max normalised score per image) -----------------
    max_scores: dict[str, float] = {}
    for img, neighbours in duplicates.items():
        for neighbour, raw_score in neighbours:
            norm = normalize_score(raw_score, method)
            if img in parent:
                max_scores[img] = max(max_scores.get(img, 0.0), norm)
            if neighbour in parent:
                max_scores[neighbour] = max(max_scores.get(neighbour, 0.0), norm)

    # --- Assemble group dicts ------------------------------------------------
    groups: list[dict] = []
    for members in components.values():
        sorted_members = sorted(members)
        images = []
        for rel_path in sorted_members:
            meta = get_image_metadata(image_dir, rel_path)
            filename = Path(rel_path).name
            images.append(
                {
                    "path": rel_path,
                    "filename": filename,
                    "size_bytes": meta["size_bytes"],
                    "width": meta["width"],
                    "height": meta["height"],
                    "score": round(max_scores.get(rel_path, 0.0), 4),
                }
            )
        groups.append({"images": images})

    # Sort: largest group first, then alphabetically by first filename
    groups.sort(key=lambda g: (-len(g["images"]), g["images"][0]["path"]))

    # Assign stable IDs after sorting
    for idx, group in enumerate(groups):
        group["id"] = idx

    return groups
