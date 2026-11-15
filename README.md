# Fortune Lab

Fortune Lab is a Flask application for collecting and exploring Philippine PCSO
lottery results. It provides historical statistics, pattern summaries, number
combinations derived from past draws, and tools for comparing saved predictions
with submitted results.

Lottery draws are random. Historical frequencies and generated combinations do
not predict or improve the odds of future draws. This project is for educational
and entertainment purposes only.

## What it does

- Scrapes PCSO results for Lotto 6/42, Mega Lotto 6/45, Super Lotto 6/49,
  Grand Lotto 6/55, and Ultra Lotto 6/58.
- Presents frequency, date, day-of-week, and pattern analyses with charts.
- Generates several historical-pattern-based combination lists.
- Optionally interprets analysis reports with a configured Ollama model.
- Records submitted draw results and compares them with available saved
  analysis snapshots.

## Requirements

- Python 3.14 or newer
- [uv](https://docs.astral.sh/uv/)
- Chrome or Chromium and an internet connection to scrape PCSO
- Ollama and a configured model only for AI analysis

## Run locally

```powershell
uv sync
Copy-Item .env.example .env
uv run python app.py
```

Open `http://127.0.0.1:5000` (or the configured `PORT`). The application uses
`app/data` by default, with separate `analysis`, `ai_analysis`, `accuracy`, and
`progress` subdirectories. Set `DATA_PATH` in `.env` to use another data
directory; the other paths default to subdirectories of it.

Scraping runs in a background thread and requires PCSO and browser access.
While it runs you can keep using the app or open other pages. Home shows a
progress bar; other pages and a scrolled Home page show a small floating
progress card. When loading finishes or fails, you get an in-app notification
with an **Analyze** shortcut and, if allowed, a desktop notification. AI
analysis is optional: configure `OLLAMA_HOST`, `OLLAMA_MODEL`, and
`OLLAMA_ENABLED`, then start Ollama separately. **Analyze with AI** queues the
request and runs it in the background, one run at a time, so a slow model
cannot cause a browser request to time out. The run appears immediately under
**History** for its result file with an "Analyzing…" badge. When it finishes,
the page shows an in-app notification and, if allowed, a desktop notification.
`OLLAMA_TIMEOUT` (seconds, default 300) limits how long the server waits on the
model. Every AI analysis is saved in History, where earlier runs can be viewed,
deleted, or compared side by side. AI output describes historical data only and
does not predict future draws.

## Configuration and deployment

Configuration defaults and environment-variable names are defined in
`app/config.py`; `.env.example` mirrors `.env` with sensitive values omitted.
Common options include `HOST`, `PORT`, `DEBUG`, `DATA_PATH`, `HEADLESS`,
`PCSO_URL`, `PAGE_TIMEOUT`, `OLLAMA_ENABLED`, `OLLAMA_HOST`, `OLLAMA_MODEL`,
`OLLAMA_TIMEOUT`, and rate-limit settings.

The default host is loopback-only. A non-loopback host requires paired basic
authentication credentials, TLS certificate and key files, disabled debug
mode, and enabled rate limits backed by shared storage. The scrape concurrency
limit is process-local; use one application process unless cross-process job
coordination is added.

## Development checks

```powershell
uv run python -m pytest
uv run ruff check app.py app tests scripts
uv run pyright
```

The quality workflow definition runs regression tests and static checks on
Linux and Windows once it is tracked in the repository.
See [AGENTS.md](./AGENTS.md) for the code layout and contributor guidance, and
[docs/API_REFERENCE.md](./docs/API_REFERENCE.md) for the current route list.
