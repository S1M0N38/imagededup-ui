"""Cache management for the .imagededup/ directory.

Manages cached encodings, duplicate results, and the user-facing discard
list.
"""

import json
import pickle
from pathlib import Path

CACHE_DIR = ".imagededup"
ENCODINGS_FILE = "encodings.pkl"
METHOD_FILE = "method.txt"
THRESHOLD_FILE = "threshold.txt"
DUPLICATES_FILE = "duplicates.json"
DISCARD_FILE = ".imagededup.txt"


def _cache_path(image_dir: Path) -> Path:
    """Return the path to the cache directory."""
    return image_dir / CACHE_DIR


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
