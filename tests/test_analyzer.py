"""Tests for imagededup_ui.analyzer module."""

from pathlib import Path
from unittest.mock import patch

from imagededup_ui.analyzer import build_groups, normalize_score


class TestNormalizeScore:
    """Tests for normalize_score."""

    def test_phash_distance_5(self):
        """Hashing: distance 5 → (64-5)/64*100 = 92.1875."""
        assert normalize_score(5, "phash") == (64 - 5) / 64 * 100

    def test_dhash_distance_0(self):
        """Hashing: distance 0 (identical) → 100%."""
        assert normalize_score(0, "dhash") == 100.0

    def test_ahash_distance_64(self):
        """Hashing: distance 64 (maximum) → 0%."""
        assert normalize_score(64, "ahash") == 0.0

    def test_whash_distance_10(self):
        """Hashing: distance 10 → (64-10)/64*100."""
        assert normalize_score(10, "whash") == (64 - 10) / 64 * 100

    def test_cnn_similarity_0_95(self):
        """CNN: similarity 0.95 → (0.95+1)/2*100 = 97.5."""
        assert normalize_score(0.95, "cnn") == 97.5

    def test_cnn_similarity_1(self):
        """CNN: similarity 1.0 (identical) → 100%."""
        assert normalize_score(1.0, "cnn") == 100.0

    def test_cnn_similarity_neg1(self):
        """CNN: similarity -1.0 (opposite) → 0%."""
        assert normalize_score(-1.0, "cnn") == 0.0


def _mock_metadata(_image_dir: Path, rel_path: str) -> dict:
    """Return fake metadata for testing build_groups."""
    return {"size_bytes": 1000, "width": 800, "height": 600}


class TestBuildGroups:
    """Tests for build_groups."""

    @patch("imagededup_ui.analyzer.get_image_metadata", side_effect=_mock_metadata)
    def test_single_connected_component(self, _mock):
        """A→B, B→C forms one group of 3; D with no dups is excluded."""
        duplicates = {
            "a.jpg": [("b.jpg", 5)],
            "b.jpg": [("a.jpg", 5), ("c.jpg", 8)],
            "c.jpg": [("b.jpg", 8)],
            "d.jpg": [],
        }
        groups = build_groups(duplicates, "phash", Path("/fake"))

        assert len(groups) == 1
        group = groups[0]
        assert group["id"] == 0
        paths = [img["path"] for img in group["images"]]
        assert paths == ["a.jpg", "b.jpg", "c.jpg"]

    @patch("imagededup_ui.analyzer.get_image_metadata", side_effect=_mock_metadata)
    def test_no_duplicates(self, _mock):
        """All empty adjacency lists → no groups."""
        duplicates = {"a.jpg": [], "b.jpg": [], "c.jpg": []}
        groups = build_groups(duplicates, "phash", Path("/fake"))

        assert groups == []

    @patch("imagededup_ui.analyzer.get_image_metadata", side_effect=_mock_metadata)
    def test_two_separate_groups(self, _mock):
        """Two separate pairs form two groups."""
        duplicates = {
            "a.jpg": [("b.jpg", 3)],
            "b.jpg": [("a.jpg", 3)],
            "x.jpg": [("y.jpg", 2), ("z.jpg", 4)],
            "y.jpg": [("x.jpg", 2)],
            "z.jpg": [("x.jpg", 4)],
        }
        groups = build_groups(duplicates, "phash", Path("/fake"))

        assert len(groups) == 2
        # Largest group first (3 images), then 2
        assert len(groups[0]["images"]) == 3
        assert len(groups[1]["images"]) == 2

    @patch("imagededup_ui.analyzer.get_image_metadata", side_effect=_mock_metadata)
    def test_images_sorted_alphabetically(self, _mock):
        """Images within a group are sorted by path."""
        duplicates = {
            "z.jpg": [("a.jpg", 5)],
            "a.jpg": [("z.jpg", 5)],
        }
        groups = build_groups(duplicates, "phash", Path("/fake"))

        paths = [img["path"] for img in groups[0]["images"]]
        assert paths == ["a.jpg", "z.jpg"]

    @patch("imagededup_ui.analyzer.get_image_metadata", side_effect=_mock_metadata)
    def test_score_computation(self, _mock):
        """Each image gets its max normalized score."""
        duplicates = {
            "a.jpg": [("b.jpg", 5)],
            "b.jpg": [("a.jpg", 5), ("c.jpg", 8)],
            "c.jpg": [("b.jpg", 8)],
        }
        groups = build_groups(duplicates, "phash", Path("/fake"))
        scores = {img["path"]: img["score"] for img in groups[0]["images"]}

        # a.jpg: max score is with b.jpg at distance 5 → (64-5)/64*100
        assert scores["a.jpg"] == round((64 - 5) / 64 * 100, 4)
        # b.jpg: max of distance 5 and 8 → distance 5 gives higher similarity
        assert scores["b.jpg"] == round((64 - 5) / 64 * 100, 4)
        # c.jpg: only neighbor is b.jpg at distance 8
        assert scores["c.jpg"] == round((64 - 8) / 64 * 100, 4)

    @patch("imagededup_ui.analyzer.get_image_metadata", side_effect=_mock_metadata)
    def test_group_metadata_fields(self, _mock):
        """Each image dict has all required fields."""
        duplicates = {
            "a.jpg": [("b.jpg", 5)],
            "b.jpg": [("a.jpg", 5)],
        }
        groups = build_groups(duplicates, "phash", Path("/fake"))
        img = groups[0]["images"][0]

        assert "path" in img
        assert "filename" in img
        assert "size_bytes" in img
        assert "width" in img
        assert "height" in img
        assert "score" in img
        assert img["filename"] == "a.jpg"

    @patch("imagededup_ui.analyzer.get_image_metadata", side_effect=_mock_metadata)
    def test_groups_sorted_by_size_then_name(self, _mock):
        """Equal-size groups sorted alphabetically by first filename."""
        duplicates = {
            "m.jpg": [("n.jpg", 5)],
            "n.jpg": [("m.jpg", 5)],
            "a.jpg": [("b.jpg", 3)],
            "b.jpg": [("a.jpg", 3)],
        }
        groups = build_groups(duplicates, "phash", Path("/fake"))

        assert len(groups) == 2
        # Both groups have size 2; "a.jpg" < "m.jpg"
        assert groups[0]["images"][0]["path"] == "a.jpg"
        assert groups[1]["images"][0]["path"] == "m.jpg"
        assert groups[0]["id"] == 0
        assert groups[1]["id"] == 1
