"""Cache management for the .imagededup/ directory.

Manages cached encodings, duplicate results, and the user-facing discard
list so that repeated runs can skip expensive image analysis.
"""

import json
import logging
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = ".imagededup"
ENCODINGS_FILE = "encodings.pkl"
METHOD_FILE = "method.txt"
THRESHOLD_FILE = "threshold.txt"
DUPLICATES_FILE = "duplicates.json"
DISCARD_FILE = ".imagededup.txt"


def _cache_path(image_dir: Path) -> Path:
    """Return the path to the cache directory."""
    return image_dir / CACHE_DIR


def is_cache_valid(image_dir: Path, method: str, threshold: float) -> bool:
    """Check if a valid cache exists for the given method and threshold.

    Args:
        image_dir: Path to the directory containing images.
        method: Deduplication method name.
        threshold: Similarity threshold value.

    Returns:
        True if the cache directory exists and its stored method and
        threshold match the requested values.
    """
    cache = _cache_path(image_dir)
    if not cache.is_dir():
        return False

    method_path = cache / METHOD_FILE
    threshold_path = cache / THRESHOLD_FILE
    encodings_path = cache / ENCODINGS_FILE
    duplicates_path = cache / DUPLICATES_FILE

    if not all(
        p.exists()
        for p in (method_path, threshold_path, encodings_path, duplicates_path)
    ):
        return False

    try:
        cached_method = method_path.read_text().strip()
        cached_threshold = float(threshold_path.read_text().strip())
    except (ValueError, OSError) as exc:
        logger.debug("Failed to read cache metadata: %s", exc)
        return False

    return cached_method == method and cached_threshold == threshold


def load_cache(image_dir: Path) -> tuple[dict, dict]:
    """Load cached encodings and duplicate results.

    Args:
        image_dir: Path to the directory containing images.

    Returns:
        A tuple of (encodings, duplicates_adjacency) loaded from cache.

    Raises:
        FileNotFoundError: If cache files do not exist.
    """
    cache = _cache_path(image_dir)
    encodings_path = cache / ENCODINGS_FILE
    duplicates_path = cache / DUPLICATES_FILE

    with open(encodings_path, "rb") as f:
        encodings = pickle.load(f)  # noqa: S301

    with open(duplicates_path) as f:
        raw = json.load(f)

    # Convert JSON lists back to tuples: {"img": [["dup", score], ...]}
    duplicates: dict[str, list[tuple[str, float]]] = {}
    for key, pairs in raw.items():
        duplicates[key] = [(name, score) for name, score in pairs]

    return encodings, duplicates


def save_cache(
    image_dir: Path,
    method: str,
    threshold: float,
    encodings: dict,
    duplicates: dict,
) -> None:
    """Write all cache files to the .imagededup/ directory.

    Args:
        image_dir: Path to the directory containing images.
        method: Deduplication method name.
        threshold: Similarity threshold value.
        encodings: Encoding map from imagededup.
        duplicates: Adjacency dict of duplicates with scores.
    """
    cache = _cache_path(image_dir)
    cache.mkdir(exist_ok=True)

    (cache / METHOD_FILE).write_text(method + "\n")
    (cache / THRESHOLD_FILE).write_text(str(threshold) + "\n")

    with open(cache / ENCODINGS_FILE, "wb") as f:
        pickle.dump(encodings, f)

    # Convert tuples to lists for JSON serialisation.
    # Scores from imagededup are numpy float32, which json.dump cannot
    # handle directly, so we cast each score to a plain Python float.
    json_duplicates: dict[str, list[list]] = {}
    for key, pairs in duplicates.items():
        json_duplicates[key] = [[name, float(score)] for name, score in pairs]

    with open(cache / DUPLICATES_FILE, "w") as f:
        json.dump(json_duplicates, f)


def load_discard_list(image_dir: Path) -> set[str]:
    """Load the discard list from .imagededup.txt.

    Args:
        image_dir: Path to the directory containing images.

    Returns:
        Set of relative file paths marked for discard.
        Returns an empty set if the file does not exist.
    """
    discard_path = image_dir / DISCARD_FILE
    if not discard_path.exists():
        return set()

    text = discard_path.read_text()
    return {line for line in text.splitlines() if line.strip()}


def save_discard_list(image_dir: Path, discarded: set[str]) -> None:
    """Write the discard list to .imagededup.txt.

    Args:
        image_dir: Path to the directory containing images.
        discarded: Set of relative file paths to write.
    """
    discard_path = image_dir / DISCARD_FILE
    lines = sorted(discarded)
    discard_path.write_text("\n".join(lines) + "\n" if lines else "")
