"""Tests for imagededup_ui.cache module."""

from imagededup_ui.cache import (
    is_cache_valid,
    load_cache,
    load_discard_list,
    save_cache,
    save_discard_list,
)


class TestSaveCacheAndIsValid:
    """Round-trip tests for save_cache and is_cache_valid."""

    def test_valid_after_save(self, tmp_path):
        """is_cache_valid returns True after save_cache with same params."""
        encodings = {"img1.jpg": b"abc"}
        duplicates = {"img1.jpg": [("img2.jpg", 5)], "img2.jpg": [("img1.jpg", 5)]}
        save_cache(tmp_path, "phash", 10.0, encodings, duplicates)

        assert is_cache_valid(tmp_path, "phash", 10.0) is True

    def test_invalid_if_method_changes(self, tmp_path):
        """is_cache_valid returns False when method differs."""
        encodings = {"img1.jpg": b"abc"}
        duplicates = {"img1.jpg": []}
        save_cache(tmp_path, "phash", 10.0, encodings, duplicates)

        assert is_cache_valid(tmp_path, "dhash", 10.0) is False

    def test_invalid_if_threshold_changes(self, tmp_path):
        """is_cache_valid returns False when threshold differs."""
        encodings = {"img1.jpg": b"abc"}
        duplicates = {"img1.jpg": []}
        save_cache(tmp_path, "phash", 10.0, encodings, duplicates)

        assert is_cache_valid(tmp_path, "phash", 5.0) is False

    def test_invalid_if_no_cache(self, tmp_path):
        """is_cache_valid returns False when no cache exists."""
        assert is_cache_valid(tmp_path, "phash", 10.0) is False


class TestLoadCache:
    """Tests for load_cache round-trip."""

    def test_round_trip(self, tmp_path):
        """save_cache then load_cache returns equivalent data."""
        encodings = {"img1.jpg": b"abc", "img2.jpg": b"def"}
        duplicates = {
            "img1.jpg": [("img2.jpg", 5)],
            "img2.jpg": [("img1.jpg", 5)],
        }
        save_cache(tmp_path, "phash", 10.0, encodings, duplicates)
        loaded_enc, loaded_dup = load_cache(tmp_path)

        assert loaded_enc == encodings
        assert loaded_dup == duplicates

    def test_round_trip_empty(self, tmp_path):
        """Round-trip with empty duplicates."""
        encodings = {"img.jpg": b"xyz"}
        duplicates = {"img.jpg": []}
        save_cache(tmp_path, "cnn", 0.9, encodings, duplicates)
        loaded_enc, loaded_dup = load_cache(tmp_path)

        assert loaded_enc == encodings
        assert loaded_dup == duplicates


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
