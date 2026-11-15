# HTTP routes

Routes are registered by the Flask application factory in `app/__init__.py`.
JSON routes generally return `{"success": true, ...}` on success and a
consistent JSON error response on failure.

## Pages

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Main page and available result files |
| GET | `/analyze/<filename>` | Generate and display an analysis report |
| GET | `/view-report/<report_filename>` | Display a saved report |
| GET | `/accuracy-dashboard` | Accuracy dashboard |
| GET | `/health` | Health status and current timestamp |
| GET | `/test-chart` | Chart.js test page |

## Scraping

| Method | Path | Purpose |
|---|---|---|
| POST | `/scrape` | Start a scrape; JSON requires `game_type`, `start_date`, and `end_date` in `YYYY-MM-DD` format |
| GET | `/api/progress/<task_id>` | Read progress for the returned task ID |

Only one scrape per application process runs at a time. Progress is written to
the configured progress directory and is cleaned up by scheduled maintenance.

## Analysis

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/analyze` | Return a compact analysis report; JSON requires `filename` |
| POST | `/api/ai-analyze` | Queue a background interpretation of a saved report with the configured Ollama model; JSON requires `filename`. Returns `202` with `ai_filename`, `status` (`queued`/`running`), `created_at`, and `already_pending` (true when an unfinished run for the same report is reused). Returns `503` when Ollama or the model is unavailable |
| GET | `/api/ollama-status` | Check Ollama and configured model availability |
| GET | `/api/analysis-history/<filename>` | List saved reports for a result file |
| GET | `/api/ai-analysis-history/<filename>` | List AI analyses for a result file, newest first, including each run's `status` and failure `error` |
| GET | `/api/ai-analysis/<ai_filename>` | Return one AI analysis; poll its `status` (`queued`, `running`, `completed`, `failed`) and `error` |
| DELETE | `/api/ai-analysis/<ai_filename>` | Delete one saved AI analysis |

New reports use `analysis_version: "2"`. Historical field names such as
`confidence_score`, `win_probability_score`, and `ultimate_confidence_score`
remain for compatibility, but their values are heuristic **points out of 100**,
not probabilities. Lists rank sampled candidates. New reports omit overdue-win
statuses and forecast windows from the legacy `next_win_probability` object;
that object now contains historical winner-gap summaries only.

Overall and day statistics include `frequency_context`: sample size, expected
frequency under a fair draw, appearance rates, and pointwise 95% Wilson
intervals. Overall statistics also include data-quality counts and exact
fair-draw baselines. Identical duplicates are removed in memory; invalid draws,
empty datasets, and conflicting duplicates return a safe `400` response.
Saved source files and older reports are not changed.

Temporal sections expose per-draw rates and observed coverage. Heatmaps retain
raw `data` counts and add `appearance_rates_percent` (null for periods without
draws) and `sample_sizes`. Frequency trend `datasets` use percentages; raw
counts remain in `count_datasets`. These are descriptive rankings, not adjusted
significance tests.

## Results and reports

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/files` | List result files |
| GET | `/api/result-files?game_type=<game>` | List result files for a supported game |
| POST | `/api/submit-actual-result` | Validate and add a draw result, then compare it with a suitable saved analysis snapshot |
| DELETE | `/api/delete-report/<report_filename>` | Delete a saved analysis report |
| GET | `/api/export-analysis/<report_filename>` | Download a saved report as JSON |

Result submissions require JSON fields `game_type`, `draw_date` (`YYYY-MM-DD`),
and `numbers`. Optional fields are `jackpot`, `winners`, and `target_filename`.
The filename must refer to a result file for the selected game.
Winner counts accept nonnegative integers, numeric strings (optionally followed
by "winner"/"winners"), and explicit unknown values such as `N/A`. Comparisons now
include `ultimate_predictions_comparison` and snapshot timing metadata.

## Accuracy

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/accuracy-analysis?game_type=<game>` | Detailed accuracy metrics; game filter is optional |
| GET | `/api/accuracy-summary?game_type=<game>` | Summary accuracy metrics; game filter is optional |
| GET | `/api/accuracy-provenance?game_type=<game>&draw_date=<date>` | Snapshot provenance; both filters are optional |
| GET | `/api/verify-result?game_type=<game>&draw_date=<date>` | Check whether a draw exists in the latest result dataset |
| GET | `/api/accuracy-files?game_type=<game>` | List saved accuracy comparisons; game filter is optional |

Detailed and summary metrics include `evaluation_context`, marking these as
descriptive comparisons and counting earlier-day versus retrospective/unverified
snapshots. Earlier-day metadata alone does not prove predictions were committed
before outcomes. All four main heuristic types are included. Game breakdowns
include the fair-draw expected matches per ticket (`36/N`).

The controlled historical evaluator is a CLI, not an HTTP endpoint:
`uv run python scripts\evaluate_analysis.py --help`. It saves separate
`evaluation_*.json` reports using the application's atomic JSON storage.

## Progress management

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/cleanup-progress` | Clean progress files; optional JSON `strategy` is `all`, `completed`, `stale`, or `old` |
