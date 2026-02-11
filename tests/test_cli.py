"""Tests for imagededup_ui.cli module."""

from pathlib import Path

from imagededup_ui.cli import get_default_threshold, parse_args


class TestParseArgs:
    """Tests for parse_args."""

    def test_defaults(self):
        """Default args when no arguments given."""
        args = parse_args([])
        assert args.image_dir == Path(".")
        assert args.method == "cnn"
        assert args.threshold is None
        assert args.port is None
        assert args.no_browser is False

    def test_custom_image_dir(self):
        """Positional argument sets image_dir."""
        args = parse_args(["/tmp/images"])
        assert args.image_dir == Path("/tmp/images")

    def test_custom_method(self):
        """--method flag sets method."""
        args = parse_args(["--method", "phash"])
        assert args.method == "phash"

    def test_custom_threshold(self):
        """--threshold flag sets threshold as float."""
        args = parse_args(["--threshold", "5.5"])
        assert args.threshold == 5.5

    def test_port_flag(self):
        """--port sets port as int."""
        args = parse_args(["--port", "8080"])
        assert args.port == 8080

    def test_no_browser_flag(self):
        """--no-browser sets no_browser to True."""
        args = parse_args(["--no-browser"])
        assert args.no_browser is True

    def test_all_flags_combined(self):
        """All flags can be used together."""
        args = parse_args(
            [
                "/tmp/images",
                "--method",
                "dhash",
                "--threshold",
                "15",
                "--port",
                "3000",
                "--no-browser",
            ]
        )
        assert args.image_dir == Path("/tmp/images")
        assert args.method == "dhash"
        assert args.threshold == 15.0
        assert args.port == 3000
        assert args.no_browser is True


class TestGetDefaultThreshold:
    """Tests for get_default_threshold."""

    def test_phash(self):
        """phash default threshold is 10.0."""
        assert get_default_threshold("phash") == 10.0

    def test_dhash(self):
        """dhash default threshold is 10.0."""
        assert get_default_threshold("dhash") == 10.0

    def test_ahash(self):
        """ahash default threshold is 10.0."""
        assert get_default_threshold("ahash") == 10.0

    def test_whash(self):
        """whash default threshold is 10.0."""
        assert get_default_threshold("whash") == 10.0

    def test_cnn(self):
        """cnn default threshold is 0.9."""
        assert get_default_threshold("cnn") == 0.9
