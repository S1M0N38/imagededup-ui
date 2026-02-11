# imagededup-ui

**Repository**: https://github.com/S1M0N38/imagededup-ui

## Overview

A CLI tool providing a web-based UI for deduplicating images in a local directory using the `imagededup` library.

> **Note**: This project is in early development. See `PRD.md` for detailed specifications of the CLI interface, web UI, and architecture.

## Development Commands

| Target | Purpose |
|--------|---------|
| `make help` | Show all available targets |
| `make install` | Install all dependencies via `uv sync` |
| `make lint` | Run ruff linter (with auto-fix) |
| `make format` | Format code (Python, Markdown, YAML, TOML) |
| `make typecheck` | Run `ty` type checker |
| `make quality` | Run lint + typecheck + format |
| `make test` | Run pytest |
| `make all` | Run all checks (lint, format, typecheck, test) |

## Important Rule

**Only run make commands when explicitly asked.** Do not proactively run `make format`, `make lint`, or other targets unless the user requests it.

## Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project config, dependencies, scripts, tool settings |
| `Makefile` | Development command shortcuts |
| `PRD.md` | Full product specification (CLI flags, web UI, file structure) |
| `src/imagededup_ui/` | Main package source (to be implemented) |
| `tests/` | Test directory |

## Development Tools

- **Package manager**: `uv`
- **Linting/formatting**: `ruff`
- **Type checking**: `ty`
- **Testing**: `pytest`
- **Commit messages**: `commitizen` (conventional commits)
- **Python version**: 3.13+

## Python 3.13+ Coding Conventions

Since this project targets Python 3.13+, use modern type annotations:

- **No `__future__` imports** needed (e.g., `from __future__ import annotations`)
- Use built-in types for annotations: `list`, `dict`, `tuple`, `set`, `frozenset`, `type`
- NOT the typing module versions: `List`, `Dict`, `Tuple`, `Set`, `FrozenSet`, `Type`

```python
# Good
def process(items: list[str]) -> dict[str, int]:
    return {item: len(item) for item in items}

# Bad
from typing import List, Dict
def process(items: List[str]) -> Dict[str, int]:
    ...
```

## Code Conventions

### Logging

Use the `logging` module with named loggers (one per module):

```python
import logging

logger = logging.getLogger(__name__)

def analyze(path: Path) -> None:
    logger.info("Analyzing %s", path)
    logger.warning("Skipping corrupted file: %s", file)
```

The CLI entry point configures the root logger level. Modules never call `logging.basicConfig()` or `print()` for operational output.

### Error Handling

- Raise specific, descriptive exceptions — not bare `Exception`.
- Use built-in exceptions where appropriate (`ValueError`, `FileNotFoundError`, `OSError`).
- Include context in messages: what failed and why.

```python
# Good
raise ValueError(f"Unknown method '{method}', expected one of: {VALID_METHODS}")

# Bad
raise Exception("invalid method")
```

### Docstrings

Use **Google-style** docstrings for all public functions, classes, and modules:

```python
def find_duplicates(image_dir: Path, method: str, threshold: float) -> dict[str, list[tuple[str, float]]]:
    """Find duplicate images in a directory.

    Args:
        image_dir: Path to the directory containing images.
        method: Deduplication method (phash, dhash, ahash, whash, cnn).
        threshold: Similarity threshold (interpretation varies by method).

    Returns:
        Adjacency dict mapping each filename to a list of
        (duplicate_filename, score) tuples.

    Raises:
        FileNotFoundError: If image_dir does not exist.
        ValueError: If method is not recognized.
    """
```

## Commit Conventions

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Allowed Scopes

| Scope | Usage |
|-------|-------|
| `cli` | CLI argument parsing and entry point |
| `analyzer` | Image analysis logic using imagededup |
| `cache` | Caching logic for `.imagededup/` directory |
| `server` | HTTP server and API endpoints |
| `ui` | Web UI (HTML, CSS, JS) |
| `docs` | Documentation (README, PRD, etc.) |
| `tests` | Test files and fixtures |
| `deps` | Dependency changes |
| `config` | Configuration files (pyproject.toml, etc.) |
| `build` | Build tooling, CI/CD, Makefile |

### Title Rules

- **Max 72 characters** for the subject line
- Use imperative mood ("add" not "added" or "adds")
- Do not end with a period
- Lowercase after type/scope
- Use the present tense ("fix" not "fixed")

### Examples

```
feat(cli): add --force flag to re-analyze images
fix(server): handle concurrent discard list writes
docs(readme): update installation instructions
test(analyzer): add tests for cnn method
deps: add imagededup v0.3.0
```

### Breaking Changes

For breaking changes, add `!` after the type/scope and a `BREAKING CHANGE:` footer:

```
feat(cli)!: change --threshold to accept 0-100 range

BREAKING CHANGE: --threshold now accepts percentage values
instead of method-specific ranges
```
