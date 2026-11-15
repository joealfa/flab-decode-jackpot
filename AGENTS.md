# Project guide

## Purpose and constraints

Fortune Lab collects Philippine PCSO lottery results and provides historical
analysis. Generated combinations are based on historical data, not predictive
odds; keep that limitation clear in code and user-facing text.

The codebase supports Python 3.14+, uses `uv`, Flask, Selenium, Pandas, NumPy,
and JSON files. Use `pyproject.toml` and `uv.lock` as dependency sources of
truth.

## Architecture

- `app.py` loads settings and runs the standalone Flask server.
- `app/__init__.py` builds isolated Flask application instances and registers
  routes, security hooks, rate limits, and the progress-cleanup scheduler.
- `app/routes/` contains HTTP handlers; `app/services/` contains shared
  analysis, result, and background-job operations.
- `app/modules/` contains the PCSO scraper, statistical and accuracy
  analyzers, AI integration, and progress tracking.
- `app/storage.py` validates contained JSON filenames and provides atomic,
  cross-process-locked JSON reads and writes.
- `app/templates/` and `app/static/` implement the browser interface.
- `app/data/` is the active mutable storage location, with `analysis/`,
  `ai_analysis/` (saved AI interpretations), `accuracy/`, and `progress/`
  subdirectories.

Scrapes run in a background thread. The concurrency semaphore is local to one
application process; progress and JSON writes use file locks. Do not assume the
semaphore coordinates multiple server processes.

## Working in this repository

- Preserve unrelated working-tree changes; inspect the diff before editing.
- Prefer existing validators, storage functions, exception types, and service
  boundaries over duplicating behavior.
- Validate user-provided filenames with `validate_filename()` before file
  access. Use `read_json()`, `write_json()`, or `update_json()` for persisted
  JSON; avoid direct writes that bypass atomic replacement and locking.
- Convert NumPy values to JSON-compatible values through the existing
  serialization layer.
- Log operational errors server-side and return safe client responses.
- Keep comments only where they explain non-obvious intent or constraints; do
  not narrate the next line of code.
- Update the README or API reference when user-visible behavior or routes
  change.

## Commands

```powershell
uv sync
uv run python app.py
uv run python -m pytest
uv run ruff check app.py app tests scripts
uv run pyright
```

The type-check command covers the application, scripts, and tests through the
`pyright` configuration in `pyproject.toml`.
