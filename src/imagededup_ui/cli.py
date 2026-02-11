"""CLI argument parsing and orchestration for imagededup-ui.

Parses command-line flags, checks cache validity, runs analysis when
needed, and hands off to the HTTP server for the review UI.
"""

import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

HASH_METHODS = ("phash", "dhash", "ahash", "whash")
ALL_METHODS = (*HASH_METHODS, "cnn")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list to parse.  Defaults to ``sys.argv[1:]``.

    Returns:
        Parsed :class:`argparse.Namespace` object.
    """
    parser = argparse.ArgumentParser(
        prog="imagededup-ui",
        description="Find and review duplicate images in a directory.",
    )
    parser.add_argument(
        "image_dir",
        nargs="?",
        default=".",
        type=Path,
        help="Path to image directory (default: current dir)",
    )
    parser.add_argument(
        "--method",
        choices=ALL_METHODS,
        default="cnn",
        help="Deduplication method (default: cnn)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Similarity threshold (method-specific default)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-analyze even if cached",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Server port (default: auto)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't auto-open browser",
    )
    return parser.parse_args(argv)


def get_default_threshold(method: str) -> float:
    """Return the default threshold for a deduplication method.

    Args:
        method: One of the supported deduplication method names.

    Returns:
        Default threshold value (10.0 for hashing methods, 0.9 for CNN).
    """
    if method in HASH_METHODS:
        return 10.0
    return 0.9


def main(argv: list[str] | None = None) -> None:
    """Entry point for the imagededup-ui CLI.

    Args:
        argv: Argument list to parse.  Defaults to ``sys.argv[1:]``.

    Raises:
        FileNotFoundError: If the specified image directory does not exist.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args(argv)
    image_dir = args.image_dir.resolve()

    if not image_dir.is_dir():
        raise FileNotFoundError(f"Directory not found: {image_dir}")

    method = args.method
    threshold = (
        args.threshold if args.threshold is not None else get_default_threshold(method)
    )

    from imagededup_ui.analyzer import build_groups, encode, find_duplicates
    from imagededup_ui.cache import is_cache_valid, load_cache, save_cache

    if not args.force and is_cache_valid(image_dir, method, threshold):
        logger.info("Using cached results")
        encodings, duplicates = load_cache(image_dir)
    else:
        logger.info("Analyzing images with method=%s threshold=%s", method, threshold)
        encodings = encode(image_dir, method)
        duplicates = find_duplicates(encodings, method, threshold)
        save_cache(image_dir, method, threshold, encodings, duplicates)

    groups = build_groups(duplicates, method, image_dir)

    if not groups:
        logger.info("No duplicates found")
        return

    logger.info("Found %d duplicate sets", len(groups))

    from imagededup_ui.server import start_server

    start_server(image_dir, groups, args.port, not args.no_browser)
