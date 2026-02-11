# Image Deduplication UI - Product Requirements Document

## Overview

A simple CLI tool that provides a web-based UI for deduplicating images in a local directory. The tool uses the `imagededup` library to analyze images and presents similar images in a browser interface where users can mark duplicates for discard.

## CLI Interface

```bash
imagededup-ui [options] [path/to/images]
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--method` | Deduplication method: `phash`, `dhash`, `ahash`, `whash`, `cnn` | `cnn` |
| `--threshold` | Similarity threshold (varies by method) | Method-specific default |
| `--port` | Specific port for HTTP server | Auto-find free port |
| `--no-browser` | Do not auto-open the browser | `false` |

### Method-Specific Threshold Defaults

| Method | Threshold Type | Default Value |
|--------|---------------|---------------|
| `phash`, `dhash`, `ahash`, `whash` | `max_distance_threshold` (0-64) | `10` |
| `cnn` | `min_similarity_threshold` (-1.0 to 1.0) | `0.9` |

## Workflow

1. **Analysis Phase**: User runs `imagededup-ui /path/to/images`
2. **Progress**: CLI shows progress using `tqdm` during image analysis
3. **Caching**: Results are saved in `.imagededup/` directory
4. **Server Launch**: HTTP server starts on a free port; unless `--no-browser` is set, the default browser opens automatically. The URL is always printed to the terminal
5. **Review**: User reviews duplicate sets in the browser and marks images to discard
6. **Live Update**: Discard list is continuously updated in `.imagededup.txt`
7. **Exit**: User presses Ctrl+C. No special cleanup needed — the discard list is written to disk on every change

## File Structure

### Artifacts Directory (`<image_dir>/.imagededup/`)

```
.imagededup/
├── encodings.pkl     # Cached encodings/hashes (pickle format)
├── method.txt        # Which method was used (e.g., "phash")
├── threshold.txt     # Threshold value used
└── duplicates.json   # Computed duplicate sets
```

**`duplicates.json` format**: Per-image adjacency dict where each key is a filename and each value is a list of `[filename, score]` pairs. Every image appears as a key (empty list if no duplicates).

### Discard List (`<image_dir>/.imagededup.txt`)

One file path per line, relative to the base image directory:
```
subdir/photo1.jpg
vacation photo.png
assets/banner.webp
```

On server start, if `.imagededup.txt` already exists, its entries are loaded and those images appear pre-marked as discarded in the UI. Users can unmark them.

> **Note**: This tool does not delete or move any files. The `.imagededup.txt` file is a plain-text list for the user to act on manually (e.g., via `xargs rm < .imagededup.txt`).

## Analysis Behavior

### First Run
- Scan all images recursively (excluding hidden files and symlinks)
- Generate encodings/hashes using selected method
- Find duplicates based on threshold (with scores enabled for UI display)
- Save artifacts to `.imagededup/`

### Subsequent Runs
- Always re-analyze images (no cache-based skipping)
- Results are saved to `.imagededup/` after each run

### Image Filtering
- **Skip**: Hidden files/directories (starting with `.`)
- **Skip**: Symbolic links
- **Support**: All formats supported by `imagededup`: JPEG, PNG, BMP, MPO, PPM, TIFF, GIF, SVG, PGM, PBM, WEBP
- **Error handling**: Corrupted/unreadable files are skipped with CLI warning

### Duplicate Grouping

The `imagededup` library returns a per-image adjacency dict (symmetric: if A→B then B→A). To present "duplicate sets" in the UI, the adjacency is converted to **connected components** using Union-Find:

- If A~B and B~C, then {A, B, C} form one set (even if A≁C)
- Only images with at least one duplicate appear in the UI
- Sets are ordered by size (largest first), then alphabetically by first filename

## Web UI

### Layout

- **Horizontal row** of similar images (one duplicate set at a time)
- **Thumbnail size**: 300px
- **Navigation**: Simple mouse-only interface

### Per-Image Information Displayed

- Filename
- File size
- Resolution
- Path: full relative path from base directory (e.g., `vacation/2024/beach/photo.jpg`)
- Similarity score (normalized to 0–100% scale; hashing: `(64 - distance) / 64 × 100`, CNN: `(similarity + 1) / 2 × 100`)

### Similarity Score Display

Each image in a duplicate set shows its **maximum similarity score to any other image in the same set**. For example, if A~B (95%) and B~C (80%):
- A shows 95% (its score with B)
- B shows 95% (its score with A)
- C shows 80% (its score with B)

### Interactions

| Action | Behavior |
|--------|----------|
| Left-click on image | Toggle discard status (add/remove from `.imagededup.txt`) |
| Discarded image | Dimmed with reduced opacity |
| Navigation between sets | Button-based (Previous/Next) |
| Current position | Displayed as "5/42" (current set of total sets) |

### UI Framework

- **Backend**: Python built-in `http.server`
- **Frontend**: Alpine.js via CDN (~17KB, declarative reactive attributes)
- **No build step required**

## HTTP API

All API routes are served by the Python `http.server` instance.

### Routes

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/` | Serve `index.html` |
| `GET` | `/static/<file>` | Serve static assets (`style.css`, `app.js`) |
| `GET` | `/api/groups` | Return all duplicate groups with metadata |
| `GET` | `/api/discard` | Return current discard list |
| `POST` | `/api/discard` | Update discard list (add/remove entries) |
| `GET` | `/images/<path>` | Serve an image file from the target directory |

### `GET /api/groups`

Returns all duplicate sets with per-image metadata.

**Response** `200 OK`:
```json
{
  "groups": [
    {
      "id": 0,
      "images": [
        {
          "path": "vacation/photo1.jpg",
          "filename": "photo1.jpg",
          "size_bytes": 245760,
          "width": 1920,
          "height": 1080,
          "score": 97.5
        }
      ]
    }
  ],
  "total_groups": 42
}
```

- `score`: Normalized similarity (0–100%) — max score to any other image in the set.
- `path`: Relative to the base image directory.
- Groups ordered by size descending, then alphabetically by first filename.

### `GET /api/discard`

**Response** `200 OK`:
```json
{
  "discarded": ["vacation/photo1.jpg", "assets/banner.webp"]
}
```

### `POST /api/discard`

Toggle an image's discard status.

**Request**:
```json
{
  "path": "vacation/photo1.jpg",
  "discard": true
}
```

**Response** `200 OK`:
```json
{
  "discarded": ["vacation/photo1.jpg", "assets/banner.webp"]
}
```

Returns the full updated discard list. The server writes `.imagededup.txt` to disk on every change.

### `GET /images/<path>`

Serves the raw image file from the target directory. `<path>` is URL-encoded, relative to the base image directory. Returns the image with the appropriate `Content-Type` header.

**Error** `404 Not Found` if the file doesn't exist.
**Error** `403 Forbidden` if the path escapes the base directory (path traversal protection).

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| No duplicates found | Print "No duplicates found" to CLI, do NOT open browser |
| Large image sets | Show all sets (no pagination limit) |
| Corrupted image | Skip with CLI warning |
| Unsupported format | Skip with CLI warning |

## Platform Support

- **Primary**: macOS, Linux
- **Browser**: Default system browser (auto-opened)

## Dependencies (managed via `uv add`)

```
imagededup  # Core deduplication library (Context7: /idealo/imagededup)
tqdm        # Progress bars during analysis
```

## Testing

A `./images` directory (git-ignored) is included with duplicate images for testing the application during development.

## Project Structure (Tentative)

```
imagededup-ui/
├── pyproject.toml
├── uv.lock
├── README.md
├── PRD.md
├── src/
│   └── imagededup_ui/
│       ├── __init__.py
│       ├── cli.py           # CLI argument parsing
│       ├── analyzer.py       # Image analysis using imagededup
│       ├── cache.py          # Caching logic for .imagededup/
│       ├── server.py         # HTTP server for web UI
│       └── static/
│           ├── index.html
│           ├── style.css
│           └── app.js
└── tests/
```

## Future Enhancements (Out of Scope for MVP)

- Keyboard navigation (arrow keys)
- Batch operations (discard all in set except one)
- Export to different formats
- Undo/redo functionality
- Dark mode
