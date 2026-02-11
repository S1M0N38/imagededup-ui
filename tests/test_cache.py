"""Tests for imagededup_ui.cache module."""

import json
import pickle

from imagededup_ui.cache import (
    load_discard_list,
    save_cache,
    save_discard_list,
)


class TestSaveCache:
    """Tests for save_cache."""

    def test_creates_cache_dir(self, tmp_path):
        """save_cache creates the .imagededup/ directory."""
        encodings = {"img1.jpg": b"abc"}
        duplicates = {"img1.jpg": [("img2.jpg", 5)], "img2.jpg": [("img1.jpg", 5)]}
        save_cache(tmp_path, "phash", 10.0, encodings, duplicates)

        cache_dir = tmp_path / ".imagededup"
        assert cache_dir.is_dir()

    def test_writes_method(self, tmp_path):
        """save_cache writes the method to method.txt."""
        save_cache(tmp_path, "phash", 10.0, {"img.jpg": b"abc"}, {"img.jpg": []})

        assert (tmp_path / ".imagededup" / "method.txt").read_text().strip() == "phash"

    def test_writes_threshold(self, tmp_path):
        """save_cache writes the threshold to threshold.txt."""
        save_cache(tmp_path, "cnn", 0.9, {"img.jpg": b"abc"}, {"img.jpg": []})

        text = (tmp_path / ".imagededup" / "threshold.txt").read_text().strip()
        assert float(text) == 0.9

    def test_writes_encodings(self, tmp_path):
        """save_cache writes encodings as pickle."""
        encodings = {"img1.jpg": b"abc", "img2.jpg": b"def"}
        save_cache(tmp_path, "phash", 10.0, encodings, {"img1.jpg": []})

        with open(tmp_path / ".imagededup" / "encodings.pkl", "rb") as f:
            loaded = pickle.load(f)  # noqa: S301
        assert loaded == encodings

    def test_writes_duplicates_json(self, tmp_path):
        """save_cache writes duplicates as JSON with float scores."""
        duplicates = {
            "img1.jpg": [("img2.jpg", 5)],
            "img2.jpg": [("img1.jpg", 5)],
        }
        save_cache(tmp_path, "phash", 10.0, {"img1.jpg": b"a"}, duplicates)

        with open(tmp_path / ".imagededup" / "duplicates.json") as f:
            loaded = json.load(f)
        assert loaded == {
            "img1.jpg": [["img2.jpg", 5.0]],
            "img2.jpg": [["img1.jpg", 5.0]],
        }


class TestDiscardList:
    """Tests for load_discard_list and save_discard_list."""

    def test_round_trip(self, tmp_path):
        """save then load returns same paths."""
        paths = {"subdir/photo1.jpg", "vacation photo.png", "assets/banner.webp"}
        save_discard_list(tmp_path, paths)
        loaded = load_discard_list(tmp_path)

        assert loaded == paths

    def test_load_missing_file(self, tmp_path):
        """load_discard_list returns empty set when file doesn't exist."""
        assert load_discard_list(tmp_path) == set()

    def test_empty_set(self, tmp_path):
        """Saving empty set creates empty file."""
        save_discard_list(tmp_path, set())
        assert load_discard_list(tmp_path) == set()
