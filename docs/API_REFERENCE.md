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

## Accuracy

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/accuracy-analysis?game_type=<game>` | Detailed accuracy metrics; game filter is optional |
| GET | `/api/accuracy-summary?game_type=<game>` | Summary accuracy metrics; game filter is optional |
| GET | `/api/accuracy-provenance?game_type=<game>&draw_date=<date>` | Snapshot provenance; both filters are optional |
| GET | `/api/verify-result?game_type=<game>&draw_date=<date>` | Check whether a draw exists in the latest result dataset |
| GET | `/api/accuracy-files?game_type=<game>` | List saved accuracy comparisons; game filter is optional |

## Progress management

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/cleanup-progress` | Clean progress files; optional JSON `strategy` is `all`, `completed`, `stale`, or `old` |
