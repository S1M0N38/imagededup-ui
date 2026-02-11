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
| `--force` | Re-analyze all images even if cached | `false` |
| `--port` | Specific port for HTTP server | Auto-find free port |

### Method-Specific Threshold Defaults

| Method | Threshold Type | Default Value |
|--------|---------------|---------------|
| `phash`, `dhash`, `ahash`, `whash` | `max_distance_threshold` (0-64) | `10` |
| `cnn` | `min_similarity_threshold` (-1.0 to 1.0) | `0.9` |

## Workflow

1. **Analysis Phase**: User runs `imagededup-ui /path/to/images`
2. **Progress**: CLI shows progress using `tqdm` during image analysis
3. **Caching**: Results are cached in `.imagededup/` directory for fast resume
4. **Server Launch**: HTTP server starts on a free port, browser opens automatically
5. **Review**: User reviews duplicate sets in the browser and marks images to discard
6. **Live Update**: Discard list is continuously updated in `.imagededup.txt`
7. **Exit**: User kills the CLI process to stop the server

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

## Analysis Behavior

### First Run
- Scan all images recursively (excluding hidden files and symlinks)
- Generate encodings/hashes using selected method
- Find duplicates based on threshold (with scores enabled for UI display)
- Save artifacts to `.imagededup/`

### Subsequent Runs
- Check if `.imagededup/` exists with matching method and threshold
- If matches: skip analysis, use cached results
- If method or threshold changed: re-analyze all images
- If `--force`: re-analyze all images regardless of cache

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
- Path relative to base directory
- Similarity score (normalized to 0–100% scale; hashing: `(64 - distance) / 64 × 100`, CNN: `(similarity + 1) / 2 × 100`)

### Interactions

| Action | Behavior |
|--------|----------|
| Left-click on image | Toggle discard status (add/remove from `.imagededup.txt`) |
| Discarded image | Shows red cross overlay |
| Navigation between sets | Button-based (Previous/Next) |
| Current position | Displayed as "5/42" (current set of total sets) |

### UI Framework

- **Backend**: Python built-in `http.server`
- **Frontend**: Lightweight JS framework via CDN (e.g., Alpine.js or petite-vue) OR vanilla JS
- **No build step required**

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
