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
- Offers **Lucky Pick** next to Home in the navigation (also available on
  mobile). Select any supported game and generate 1 to 20 random six-number
  combinations in the modal. Picks are generated entirely in the browser,
  are not saved or based on historical data, and are cleared when the modal
  closes. Random picks do not predict results or improve winning odds.
- Optionally interprets analysis reports with a configured Ollama model.
- Records submitted draw results and compares them with available saved
  analysis snapshots.

## Analysis correctness and interpretation

Analysis validates draw numbers and dates, normalizes winner counts and weekday
labels, and excludes identical duplicate draws **in memory**. Conflicting
duplicates are rejected; original datasets are not rewritten. Report coverage
uses actual observed dates and is not a guarantee of complete PCSO history.
Existing saved reports are unchanged: re-run analysis to apply the fixes.

Scores are heuristic points out of 100, **not confidence percentages or winning
probabilities**. Lists rank sampled candidates, not every possible combination.
Winner-gap summaries describe historical intervals; there is no "overdue" win
forecast. Pattern picks enforce their stated carryover count and explain when
that constraint allows fewer unique combinations than requested.

Reports include per-draw appearance rates, fair-draw expected frequencies, and
pointwise 95% Wilson intervals. These are not simultaneous significance tests:
examining many numbers or periods can reveal ordinary chance fluctuations.
Temporal comparisons and heatmaps use appearance rates and report sample sizes;
calendar-month and ISO-week groups combine years and may have partial coverage.

The Accuracy dashboard shows descriptive saved-pick comparisons, including
combined/Ultimate picks. It identifies retrospective or unverified snapshots;
its highest observed average does not establish a superior algorithm.
Game filters with no comparisons show an empty state; switching back to a game
with data or retrying a failed request restores the charts and tables.

## Historical walk-forward evaluation

Run the CLI without blocking Flask requests:

```powershell
uv run python scripts\evaluate_analysis.py --filename result_Super_Lotto_6-49_20261115.json --draws 50 --min-training 50 --tickets 5 --seed 42
```

The latest `--draws` unique draws form the evaluation period. Each fold generates
frequency, winner-subset, pattern, and combined/Ultimate picks using **only
earlier draws**, then compares them with the same number of unique random
tickets. Daily subgroup picks and AI interpretations are not evaluated.
Insufficient history or an unequal ticket budget is an explicit error.

Repeat `--filename` to evaluate multiple datasets separately; games and
overlapping datasets are never pooled. Use `--output evaluation_my_check.json`
to choose a JSON basename in the configured analysis directory. Otherwise a
timestamped `evaluation_*.json` report is created. Evaluations are kept separate
from dashboard snapshots, and source result files remain unchanged.

Reports record seeds, analysis/runtime versions, dataset and training hashes,
per-draw tickets, match distributions, and exact fair-draw baselines. They include
approximate draw-level bootstrap intervals and paired differences against random
picks, with Bonferroni-adjusted intervals across the four comparisons. Small
samples and overlapping training histories limit inference.

These are **retrospective simulations**, not proof of picks committed before
real draws. No weight tuning is performed. If results guide algorithm changes,
reserve a separate untouched evaluation period; do not tune and claim success
on the same outcomes or cherry-pick seeds. Results do not establish improved
winning odds.

## Requirements

- Python 3.14 or newer (default: Python 3.15.2)
- [uv](https://docs.astral.sh/uv/)
- Chrome or Chromium and an internet connection to scrape PCSO
- Ollama and a configured model only for AI analysis

The locked dependencies and regression suite have been validated locally on
Python 3.14.10 and 3.15.2. Python 3.14 remains the minimum supported version.
On Python 3.15, the locked `pydantic-core` and `PyYAML` currently build from
source; installation may require Rust and native build tools (including
Microsoft C++ Build Tools on Windows).

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

With Node.js installed, run the Lucky Pick and accuracy-dashboard regression
tests with `node --test tests\test_lucky_pick.cjs tests\test_accuracy_dashboard.cjs`.

The quality workflow definition runs regression tests and static checks on
Python 3.14 and 3.15 on Linux and Windows.
See [AGENTS.md](./AGENTS.md) for the code layout and contributor guidance, and
[docs/API_REFERENCE.md](./docs/API_REFERENCE.md) for the current route list.

## Disclaimer

The lotto results and related data collected and displayed by this project are
based on publicly available PCSO publications and are provided for historical
reference and analysis only.

This project is not affiliated with, associated with, authorized by, or
officially endorsed by the Philippine Charity Sweepstakes Office (PCSO).

For official and verified lotto results, please visit the
[official PCSO website](https://www.pcso.gov.ph).