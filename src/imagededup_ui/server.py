"""HTTP server for the imagededup-ui web interface.

Serves the Alpine.js frontend, image files from the target directory,
and a JSON API for managing duplicate groups and the discard list.
"""

import json
import logging
import mimetypes
import socket
import socketserver
import webbrowser
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

from imagededup_ui.cache import load_discard_list, save_discard_list

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


class DedupRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the imagededup-ui web interface.

    Routes:
        GET /               — Serve index.html
        GET /static/<file>  — Serve static assets (css, js)
        GET /api/groups     — Return all duplicate groups as JSON
        GET /api/discard    — Return the current discard list as JSON
        POST /api/discard   — Toggle discard status for a path
        GET /images/<path>  — Serve an image from the target directory
    """

    def do_GET(self) -> None:
        """Handle GET requests."""
        path = unquote(self.path)

        if path == "/":
            self._serve_static_file("index.html")
        elif path.startswith("/static/"):
            rel = path[len("/static/"):]
            self._serve_static_file(rel)
        elif path == "/api/groups":
            self._handle_api_groups()
        elif path == "/api/discard":
            self._handle_api_discard_get()
        elif path.startswith("/images/"):
            rel = path[len("/images/"):]
            self._serve_image(rel)
        else:
            self._send_error(404, "Not found")

    def do_POST(self) -> None:
        """Handle POST requests."""
        path = unquote(self.path)

        if path == "/api/discard":
            self._handle_api_discard_post()
        else:
            self._send_error(404, "Not found")

    # --- API handlers --------------------------------------------------------

    def _handle_api_groups(self) -> None:
        """Return all duplicate groups with metadata."""
        groups = self.server.groups  # type: ignore[attr-defined]
        payload = {
            "groups": groups,
            "total_groups": len(groups),
        }
        self._send_json(payload)

    def _handle_api_discard_get(self) -> None:
        """Return the current discard list."""
        discarded = self.server.discarded  # type: ignore[attr-defined]
        self._send_json({"discarded": sorted(discarded)})

    def _handle_api_discard_post(self) -> None:
        """Toggle discard status for a single image path."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_error(400, f"Invalid JSON: {exc}")
            return

        image_path = data.get("path")
        discard = data.get("discard")

        if not isinstance(image_path, str) or not isinstance(discard, bool):
            self._send_error(400, "Expected {\"path\": str, \"discard\": bool}")
            return

        discarded: set[str] = self.server.discarded  # type: ignore[attr-defined]
        image_dir: Path = self.server.image_dir  # type: ignore[attr-defined]

        if discard:
            discarded.add(image_path)
        else:
            discarded.discard(image_path)

        save_discard_list(image_dir, discarded)
        self._send_json({"discarded": sorted(discarded)})

    # --- File serving --------------------------------------------------------

    def _serve_static_file(self, rel_path: str) -> None:
        """Serve a file from the static/ directory.

        Args:
            rel_path: Path relative to the static directory.
        """
        safe_path = STATIC_DIR / rel_path
        try:
            safe_path = safe_path.resolve()
        except (OSError, ValueError):
            self._send_error(404, "Not found")
            return

        if not safe_path.is_relative_to(STATIC_DIR.resolve()):
            self._send_error(403, "Forbidden")
            return

        if not safe_path.is_file():
            self._send_error(404, "Not found")
            return

        content_type, _ = mimetypes.guess_type(str(safe_path))
        content_type = content_type or "application/octet-stream"

        content = safe_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _serve_image(self, rel_path: str) -> None:
        """Serve an image file from the target directory.

        Args:
            rel_path: Path relative to the image directory.
        """
        image_dir: Path = self.server.image_dir  # type: ignore[attr-defined]
        full_path = image_dir / rel_path
        try:
            full_path = full_path.resolve()
        except (OSError, ValueError):
            self._send_error(404, "Not found")
            return

        if not full_path.is_relative_to(image_dir.resolve()):
            self._send_error(403, "Forbidden")
            return

        if not full_path.is_file():
            self._send_error(404, "Not found")
            return

        content_type, _ = mimetypes.guess_type(str(full_path))
        content_type = content_type or "application/octet-stream"

        content = full_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    # --- Helpers -------------------------------------------------------------

    def _send_json(self, data: dict) -> None:
        """Send a JSON response with 200 status.

        Args:
            data: Dict to serialise as JSON.
        """
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, code: int, message: str) -> None:
        """Send a plain-text error response.

        Args:
            code: HTTP status code.
            message: Error message body.
        """
        body = message.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """Suppress default access logs; route through logger.debug instead."""
        logger.debug(format, *args)


class DedupServer(socketserver.TCPServer):
    """TCP server that carries application state for the request handler.

    Attributes:
        image_dir: Resolved path to the target image directory.
        groups: List of duplicate-group dicts from the analyser.
        discarded: Mutable set of relative paths marked for discard.
    """

    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        image_dir: Path,
        groups: list[dict],
        discarded: set[str],
    ) -> None:
        self.image_dir = image_dir
        self.groups = groups
        self.discarded = discarded
        super().__init__(server_address, DedupRequestHandler)


def find_free_port() -> int:
    """Find an available TCP port by binding to port 0.

    Returns:
        An unused port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def start_server(
    image_dir: Path,
    groups: list[dict],
    port: int | None,
    open_browser: bool,
) -> None:
    """Start the HTTP server and block until interrupted.

    Args:
        image_dir: Resolved path to the directory containing images.
        groups: List of duplicate-group dicts produced by the analyser.
        port: TCP port to listen on.  If ``None``, a free port is chosen.
        open_browser: Whether to open the URL in the default browser.
    """
    if port is None:
        port = find_free_port()

    discarded = load_discard_list(image_dir)
    server = DedupServer(("", port), image_dir, groups, discarded)

    url = f"http://localhost:{port}"
    logger.info("Serving on %s  (Ctrl+C to stop)", url)

    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        server.server_close()
