"""Tests for imagededup_ui.server module."""

import json
import threading
from http.client import HTTPConnection
from pathlib import Path

import pytest

from imagededup_ui.server import DedupServer, find_free_port


@pytest.fixture()
def image_dir(tmp_path):
    """Create a temporary image directory with a small test image."""
    # Minimal valid JPEG (smallest possible)
    # SOI + APP0 + SOF + SOS + EOI
    jpeg_bytes = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
        b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
        b"\x1f\x1e\x1d\x1a\x1c\x1c $.\x27 \",.+\x1c\x1c(7),01444\x1f\x27"
        b"9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08"
        b"\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03"
        b"\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12"
        b"!1A\x06\x13Qa\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1"
        b"\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\x27()*456789:CDEFGHIJ"
        b"STUVWXYZ\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd2\x8a(\x03"
        b"\xff\xd9"
    )
    (tmp_path / "test.jpg").write_bytes(jpeg_bytes)

    # Create a subdirectory with another image for path tests
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "nested.jpg").write_bytes(jpeg_bytes)

    return tmp_path


@pytest.fixture()
def sample_groups():
    """Return a minimal groups list matching the analyser output format."""
    return [
        {
            "id": 0,
            "images": [
                {
                    "path": "test.jpg",
                    "filename": "test.jpg",
                    "size_bytes": 1024,
                    "width": 100,
                    "height": 100,
                    "score": 95.0,
                },
                {
                    "path": "subdir/nested.jpg",
                    "filename": "nested.jpg",
                    "size_bytes": 1024,
                    "width": 100,
                    "height": 100,
                    "score": 95.0,
                },
            ],
        }
    ]


@pytest.fixture()
def server(image_dir, sample_groups):
    """Start a DedupServer on a free port in a background thread."""
    port = find_free_port()
    srv = DedupServer(("127.0.0.1", port), image_dir, sample_groups, set())
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()


@pytest.fixture()
def conn(server):
    """Return an HTTPConnection to the test server."""
    host, port = server.server_address
    return HTTPConnection(host, port, timeout=5)


class TestStaticRoutes:
    """Test serving of static files."""

    def test_root_returns_html(self, conn):
        """GET / returns 200 with HTML content."""
        conn.request("GET", "/")
        resp = conn.getresponse()

        assert resp.status == 200
        assert "text/html" in resp.getheader("Content-Type")
        body = resp.read().decode()
        assert "imagededup" in body

    def test_static_css_returns_css(self, conn):
        """GET /static/style.css returns 200 with CSS content."""
        conn.request("GET", "/static/style.css")
        resp = conn.getresponse()

        assert resp.status == 200
        assert "text/css" in resp.getheader("Content-Type")
        body = resp.read().decode()
        assert "--bg:" in body

    def test_static_js_returns_js(self, conn):
        """GET /static/app.js returns 200 with JS content."""
        conn.request("GET", "/static/app.js")
        resp = conn.getresponse()

        assert resp.status == 200
        body = resp.read().decode()
        assert "dedupApp" in body

    def test_static_not_found(self, conn):
        """GET /static/nonexistent returns 404."""
        conn.request("GET", "/static/does-not-exist.txt")
        resp = conn.getresponse()
        resp.read()

        assert resp.status == 404


class TestApiGroups:
    """Test the /api/groups endpoint."""

    def test_returns_groups_json(self, conn, sample_groups):
        """GET /api/groups returns correct JSON structure."""
        conn.request("GET", "/api/groups")
        resp = conn.getresponse()
        data = json.loads(resp.read())

        assert resp.status == 200
        assert data["total_groups"] == 1
        assert len(data["groups"]) == 1
        assert data["groups"][0]["images"][0]["path"] == "test.jpg"
        assert data["groups"][0]["images"][0]["score"] == 95.0


class TestApiDiscard:
    """Test the /api/discard endpoints."""

    def test_discard_initially_empty(self, conn):
        """GET /api/discard returns empty list initially."""
        conn.request("GET", "/api/discard")
        resp = conn.getresponse()
        data = json.loads(resp.read())

        assert resp.status == 200
        assert data["discarded"] == []

    def test_add_to_discard(self, conn):
        """POST /api/discard with discard=true adds path."""
        body = json.dumps({"path": "test.jpg", "discard": True})
        conn.request(
            "POST",
            "/api/discard",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        data = json.loads(resp.read())

        assert resp.status == 200
        assert "test.jpg" in data["discarded"]

    def test_remove_from_discard(self, conn):
        """POST /api/discard with discard=false removes path."""
        # First add
        body = json.dumps({"path": "test.jpg", "discard": True})
        conn.request(
            "POST",
            "/api/discard",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        conn.getresponse().read()

        # Then remove
        body = json.dumps({"path": "test.jpg", "discard": False})
        conn.request(
            "POST",
            "/api/discard",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        data = json.loads(resp.read())

        assert resp.status == 200
        assert "test.jpg" not in data["discarded"]

    def test_discard_persists_to_file(self, conn, image_dir):
        """Discard list is written to .imagededup.txt on disk."""
        body = json.dumps({"path": "test.jpg", "discard": True})
        conn.request(
            "POST",
            "/api/discard",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        conn.getresponse().read()

        discard_file = image_dir / ".imagededup.txt"
        assert discard_file.exists()
        assert "test.jpg" in discard_file.read_text()

    def test_discard_invalid_json(self, conn):
        """POST /api/discard with invalid JSON returns 400."""
        conn.request(
            "POST",
            "/api/discard",
            body="not json",
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        resp.read()

        assert resp.status == 400

    def test_discard_missing_fields(self, conn):
        """POST /api/discard with missing fields returns 400."""
        body = json.dumps({"path": "test.jpg"})
        conn.request(
            "POST",
            "/api/discard",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        resp.read()

        assert resp.status == 400


class TestImageServing:
    """Test the /images/ endpoint."""

    def test_serve_image(self, conn):
        """GET /images/<path> serves an image file."""
        conn.request("GET", "/images/test.jpg")
        resp = conn.getresponse()
        body = resp.read()

        assert resp.status == 200
        assert "image" in resp.getheader("Content-Type")
        assert len(body) > 0

    def test_serve_nested_image(self, conn):
        """GET /images/subdir/nested.jpg serves a nested image."""
        conn.request("GET", "/images/subdir/nested.jpg")
        resp = conn.getresponse()
        body = resp.read()

        assert resp.status == 200
        assert len(body) > 0

    def test_path_traversal_blocked(self, conn):
        """GET /images/../../etc/passwd returns 403."""
        conn.request("GET", "/images/../../etc/passwd")
        resp = conn.getresponse()
        resp.read()

        assert resp.status == 403

    def test_image_not_found(self, conn):
        """GET /images/nonexistent.jpg returns 404."""
        conn.request("GET", "/images/no-such-file.jpg")
        resp = conn.getresponse()
        resp.read()

        assert resp.status == 404


class TestFindFreePort:
    """Test the find_free_port utility."""

    def test_returns_positive_int(self):
        """find_free_port returns a positive port number."""
        port = find_free_port()
        assert isinstance(port, int)
        assert port > 0
