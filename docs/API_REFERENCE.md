# API Reference

Complete API documentation for Fortune Lab: Decoding the Jackpot

## Base URL

```
http://localhost:5000
```

## Authentication

Currently, no authentication is required. This is recommended for production deployments.

## Response Format

All API responses follow this structure:

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Optional success message"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error message description",
  "details": { ... }
}
```

## Security Headers

All responses include the following security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (production only)

---

## Web Routes

### 1. Home Page

**Endpoint:** `GET /`

**Description:** Main landing page with result file browser, scraping form, and file management.

**Response:** HTML page

**Template:** `index.html`

**Data Provided:**
- `result_files`: List of available result files with metadata

---

### 2. Analysis Dashboard

**Endpoint:** `GET /analyze/<filename>`

**Description:** Generate and display analysis for a result file

**Parameters:**
- `filename` (path): Name of the result JSON file

**Response:** HTML page with analysis dashboard

**Template:** `dashboard.html`

**Data Provided:**
- `data`: Original lottery data
- `overall_stats`: Overall statistics
- `day_analysis`: Day-specific analysis
- `top_predictions`: Top 5 predictions
- `winning_predictions`: Winner-optimized predictions
- `pattern_predictions`: Pattern-based predictions
- `pattern_analysis`: Consecutive pattern analysis
- `temporal_patterns`: Temporal analysis
- `historical_observations`: Historical insights
- `ultimate_predictions`: Ultimate predictions
- `chart_data`: Chart visualization data
- `filename`: Source filename
- `report_filename`: Generated report filename

**Example:**
```
GET /analyze/result_Lotto_6-42_20251030.json
```

---

### 3. View Historical Report

**Endpoint:** `GET /view-report/<report_filename>`

**Description:** View a previously generated analysis report

**Parameters:**
- `report_filename` (path): Name of the analysis report JSON file

**Response:** HTML page (same as dashboard)

**Example:**
```
GET /view-report/analysis_result_Lotto_6-42_20251030_20251030_120530.json
```

---

### 4. Accuracy Dashboard

**Endpoint:** `GET /accuracy-dashboard`

**Description:** Dashboard for viewing prediction accuracy analysis and comparisons

**Response:** HTML page

**Template:** `accuracy_dashboard.html`

---

### 5. Test Chart

**Endpoint:** `GET /test-chart`

**Description:** Test page to verify Chart.js functionality

**Response:** HTML page with sample charts

---

## API Endpoints

### 1. Scrape Lottery Data

**Endpoint:** `POST /scrape`

**Description:** Initiate lottery data scraping from PCSO website

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "game_type": "Lotto 6/42",
  "start_date": "2015-01-01",
  "end_date": "2026-02-15"
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| game_type | string | Yes | Game type (see valid values below) |
| start_date | string | Yes | Start date (YYYY-MM-DD format) |
| end_date | string | Yes | End date (YYYY-MM-DD format) |

**Valid Game Types:**
- `Lotto 6/42`
- `Mega Lotto 6/45`
- `Super Lotto 6/49`
- `Grand Lotto 6/55`
- `Ultra Lotto 6/58`

**Success Response (200):**
```json
{
  "success": true,
  "task_id": "uuid-string",
  "message": "Scraping started"
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": "Missing required fields"
}
```

**Notes:**
- Validates date range against PCSO available data
- Returns cached results if data file already exists
- Runs scraping in a background thread

**Example:**
```bash
curl -X POST http://localhost:5000/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "game_type": "Lotto 6/42",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }'
```

---

### 2. Get Scraping Progress

**Endpoint:** `GET /api/progress/<task_id>`

**Description:** Get real-time progress for a scraping task

**Parameters:**
- `task_id` (path): UUID returned from scrape endpoint

**Success Response (200):**
```json
{
  "success": true,
  "progress": {
    "task_id": "uuid-string",
    "status": "in-progress",
    "current": 250,
    "total": 500,
    "percentage": 50,
    "message": "Extracting results: 250/500 rows...",
    "started_at": 1698765432.123,
    "updated_at": 1698765450.456
  }
}
```

**Status Values:**
- `started`: Task initiated
- `in-progress`: Task running
- `completed`: Task finished successfully
- `failed`: Task failed with error

**Completed Response:**
```json
{
  "success": true,
  "progress": {
    "task_id": "uuid-string",
    "status": "completed",
    "percentage": 100,
    "message": "Scraped 500 draws successfully",
    "result": {
      "success": true,
      "filename": "result_Lotto_6-42_20251030.json",
      "total_draws": 500,
      "cached": false
    }
  }
}
```

**Error Response (404):**
```json
{
  "success": false,
  "error": "Task not found"
}
```

**Example:**
```bash
curl http://localhost:5000/api/progress/123e4567-e89b-12d3-a456-426614174000
```

---

### 3. Analyze Data (API)

**Endpoint:** `POST /api/analyze`

**Description:** Generate analysis for a result file (returns JSON)

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "filename": "result_Lotto_6-42_20251030.json"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "game_type": "Lotto 6/42",
    "total_draws": 500
  },
  "overall_stats": { ... },
  "day_analysis": { ... },
  "top_predictions": [ ... ],
  "winning_predictions": [ ... ],
  "chart_data": { ... }
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"filename": "result_Lotto_6-42_20251030.json"}'
```

---

### 4. AI-Powered Analysis

**Endpoint:** `POST /api/ai-analyze`

**Description:** Generate AI-powered interpretation of a lottery analysis using Ollama

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "filename": "analysis_result_Lotto_6-42_20251030_20260215_120530.json"
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| filename | string | Yes | Analysis or result filename. If a result file is provided, the latest analysis for it will be used. |

**Success Response (200):**
```json
{
  "success": true,
  "model": "llama3.1:8b",
  "game_type": "Lotto 6/42",
  "analysis": "## Executive Summary\n...(markdown content)...",
  "total_draws_analyzed": 500,
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-12-31"
  }
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": "AI analysis is not enabled. Set OLLAMA_ENABLED=True in configuration."
}
```

**Error Response (500):**
```json
{
  "success": false,
  "error": "Ollama is not running. Please start Ollama service.",
  "details": { "error": "Connection refused" }
}
```

**Prerequisites:**
- Ollama must be running (`ollama serve`)
- Configured model must be available (`ollama pull llama3.1:8b`)
- `OLLAMA_ENABLED=True` in configuration

**Example:**
```bash
curl -X POST http://localhost:5000/api/ai-analyze \
  -H "Content-Type: application/json" \
  -d '{"filename": "analysis_result_Lotto_6-42_20251030_20260215_120530.json"}'
```

---

### 5. Ollama Status

**Endpoint:** `GET /api/ollama-status`

**Description:** Check Ollama service status and model availability

**Success Response (200):**
```json
{
  "success": true,
  "status": {
    "running": true,
    "model_available": true,
    "available_models": ["llama3.1:8b", "llama3.2:3b"],
    "configured_model": "llama3.1:8b"
  }
}
```

**Example:**
```bash
curl http://localhost:5000/api/ollama-status
```

---

### 6. List Result Files

**Endpoint:** `GET /api/files`

**Description:** Get list of all available result files

**Success Response (200):**
```json
{
  "success": true,
  "files": [
    {
      "filename": "result_Lotto_6-42_20251030.json",
      "game_type": "Lotto 6/42",
      "total_draws": 500,
      "date_range": "2024-01-01 to 2024-12-31",
      "scraped_at": "2026-02-15 12:00:00"
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:5000/api/files
```

---

### 7. Get Result Files by Game Type

**Endpoint:** `GET /api/result-files`

**Description:** Get result files filtered by a specific game type

**Query Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| game_type | string | Yes | Game type (e.g., "Lotto 6/42") |

**Success Response (200):**
```json
{
  "success": true,
  "files": [
    {
      "filename": "result_Lotto_6-42_20251030.json",
      "display_name": "Lotto 6/42 - 2024-01-01 to 2024-12-31 (500 draws)",
      "end_date": "2024-12-31",
      "total_draws": 500,
      "scraped_at": "2026-02-15 12:00:00"
    }
  ]
}
```

**Example:**
```bash
curl "http://localhost:5000/api/result-files?game_type=Lotto%206/42"
```

---

### 8. Get Analysis History

**Endpoint:** `GET /api/analysis-history/<filename>`

**Description:** Get all analysis reports for a specific result file

**Parameters:**
- `filename` (path): Name of the result JSON file

**Success Response (200):**
```json
{
  "success": true,
  "reports": [
    {
      "filename": "analysis_result_Lotto_6-42_20251030_20260215_120530.json",
      "analyzed_at": "2026-02-15 12:05:30",
      "created_at": "2026-02-15 12:05:30",
      "size": 524288
    }
  ],
  "count": 5
}
```

**Example:**
```bash
curl http://localhost:5000/api/analysis-history/result_Lotto_6-42_20251030.json
```

---

### 9. Submit Actual Result

**Endpoint:** `POST /api/submit-actual-result`

**Description:** Submit actual draw result for accuracy tracking and add to historical dataset

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "game_type": "Lotto 6/42",
  "draw_date": "2026-02-15",
  "numbers": [5, 12, 23, 34, 38, 42],
  "jackpot": "₱50,000,000",
  "winners": "2",
  "target_filename": "result_Lotto_6-42_20251030.json"
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| game_type | string | Yes | Game type |
| draw_date | string | Yes | Draw date (YYYY-MM-DD) |
| numbers | array | Yes | Array of 6 unique integers |
| jackpot | string | No | Jackpot amount (default: "N/A") |
| winners | string | No | Number of winners (default: "N/A") |
| target_filename | string | No | Specific result file to update |

**Success Response (200):**
```json
{
  "success": true,
  "message": "Actual result added successfully",
  "accuracy_results": {
    "actual_numbers": [5, 12, 23, 34, 38, 42],
    "draw_date": "2026-02-15",
    "game_type": "Lotto 6/42",
    "top_predictions_comparison": [ ... ],
    "winning_predictions_comparison": [ ... ],
    "pattern_predictions_comparison": [ ... ],
    "ultimate_predictions_comparison": [ ... ]
  },
  "result_file": "result_Lotto_6-42_20251030.json",
  "total_draws": 501
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/submit-actual-result \
  -H "Content-Type: application/json" \
  -d '{
    "game_type": "Lotto 6/42",
    "draw_date": "2026-02-15",
    "numbers": [5, 12, 23, 34, 38, 42]
  }'
```

---

### 10. Delete Analysis Report

**Endpoint:** `DELETE /api/delete-report/<report_filename>`

**Description:** Delete an analysis report

**Parameters:**
- `report_filename` (path): Name of the analysis report file

**Success Response (200):**
```json
{
  "success": true,
  "message": "Report deleted successfully"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:5000/api/delete-report/analysis_result_Lotto_6-42_20251030_20260215_120530.json
```

---

### 11. Export Analysis Report

**Endpoint:** `GET /api/export-analysis/<report_filename>`

**Description:** Export analysis report as downloadable JSON

**Parameters:**
- `report_filename` (path): Name of the analysis report file

**Success Response (200):**
- Content-Type: `application/json`
- Content-Disposition: `attachment; filename=<report_filename>`
- Body: Complete analysis report JSON

**Example:**
```bash
curl -O -J http://localhost:5000/api/export-analysis/analysis_result_Lotto_6-42_20251030_20260215_120530.json
```

---

### 12. Cleanup Progress Files

**Endpoint:** `POST /api/cleanup-progress`

**Description:** Manually trigger cleanup of old progress files

**Content-Type:** `application/json`

**Request Body (Optional):**
```json
{
  "max_age_seconds": 300
}
```

**Parameters:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| max_age_seconds | integer | No | 300 | Maximum age in seconds for completed tasks |

**Success Response (200):**
```json
{
  "success": true,
  "cleaned_count": 5,
  "message": "Cleaned up 5 progress file(s)"
}
```

**Notes:** Progress files are also cleaned automatically every 5 minutes via APScheduler with multi-tier cleanup (completed: 3min, stale: 10min, old: 24h).

**Example:**
```bash
curl -X POST http://localhost:5000/api/cleanup-progress \
  -H "Content-Type: application/json" \
  -d '{"max_age_seconds": 600}'
```

---

### 13. Accuracy Analysis

**Endpoint:** `GET /api/accuracy-analysis`

**Description:** Get comprehensive accuracy analysis across all submitted results

**Query Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| game_type | string | No | Filter by game type (e.g., "Lotto 6/42") |

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "total_submissions": 10,
    "game_types": ["Lotto 6/42"],
    "accuracy_by_algorithm": { ... },
    "overall_accuracy": { ... }
  }
}
```

**Example:**
```bash
curl "http://localhost:5000/api/accuracy-analysis?game_type=Lotto%206/42"
```

---

### 14. Accuracy Summary

**Endpoint:** `GET /api/accuracy-summary`

**Description:** Get quick accuracy summary metrics

**Query Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| game_type | string | No | Filter by game type |

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "total_submissions": 10,
    "average_matches": 1.5,
    "best_match": 3,
    "accuracy_by_algorithm": { ... }
  }
}
```

**Example:**
```bash
curl "http://localhost:5000/api/accuracy-summary?game_type=Mega%20Lotto%206/45"
```

---

### 15. Accuracy Provenance

**Endpoint:** `GET /api/accuracy-provenance`

**Description:** Get detailed provenance/audit trail for accuracy submissions

**Query Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| game_type | string | No | Filter by game type |
| draw_date | string | No | Filter by draw date (YYYY-MM-DD) |

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "entries": [
      {
        "game_type": "Lotto 6/42",
        "draw_date": "2026-02-15",
        "snapshot_context": { ... },
        "algorithm_summaries": { ... }
      }
    ]
  }
}
```

**Example:**
```bash
curl "http://localhost:5000/api/accuracy-provenance?game_type=Lotto%206/42&draw_date=2026-02-15"
```

---

### 16. Verify Result Integrity

**Endpoint:** `GET /api/verify-result`

**Description:** Verify whether a submitted draw result exists in the historical dataset and whether it was originally scraped or manually added

**Query Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| game_type | string | Yes | Game type (e.g., "Lotto 6/42") |
| draw_date | string | Yes | Draw date (YYYY-MM-DD) |

**Success Response (200) - Found:**
```json
{
  "success": true,
  "exists": true,
  "is_original": true,
  "message": "Draw result for 2026-02-15 found in original scraped data",
  "data": {
    "source_file": "result_Lotto_6-42_20260215.json",
    "draw_details": {
      "date": "02/15/2026",
      "numbers": [5, 12, 23, 34, 38, 42],
      "jackpot": "₱50,000,000",
      "winners": "2",
      "day_of_week": "Sunday"
    },
    "original_cutoff_date": "2026-02-15"
  }
}
```

**Success Response (200) - Not Found:**
```json
{
  "success": true,
  "exists": false,
  "message": "Draw result for 2026-02-15 not found in historical data",
  "data": {
    "source_file": "result_Lotto_6-42_20260215.json",
    "total_draws_in_file": 500
  }
}
```

**Example:**
```bash
curl "http://localhost:5000/api/verify-result?game_type=Lotto%206/42&draw_date=2026-02-15"
```

---

### 17. List Accuracy Files

**Endpoint:** `GET /api/accuracy-files`

**Description:** List all accuracy comparison files

**Query Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| game_type | string | No | Filter by game type |

**Success Response (200):**
```json
{
  "success": true,
  "total": 10,
  "data": [
    {
      "filename": "accuracy_Lotto_6-42_20260215.json",
      "game_type": "Lotto 6/42",
      "draw_date": "2026-02-15",
      "actual_numbers": [5, 12, 23, 34, 38, 42],
      "timestamp": "2026-02-15T12:00:00"
    }
  ]
}
```

**Example:**
```bash
curl "http://localhost:5000/api/accuracy-files?game_type=Lotto%206/42"
```

---

### 18. Health Check

**Endpoint:** `GET /health`

**Description:** Application health check endpoint

**Success Response (200):**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-16T12:00:00.000000"
}
```

**Example:**
```bash
curl http://localhost:5000/health
```

---

## Data Models

### Result File Structure

```json
{
  "game_type": "Lotto 6/42",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "total_draws": 500,
  "scraped_at": "2026-02-15 12:00:00",
  "filename": "result_Lotto_6-42_20241231.json",
  "cached": false,
  "results": [
    {
      "game": "Lotto 6/42",
      "date": "12/31/2024",
      "day_of_week": "Tuesday",
      "numbers": [5, 12, 23, 34, 38, 42],
      "jackpot": "₱50,000,000",
      "winners": "2"
    }
  ]
}
```

### Analysis Report Structure

```json
{
  "analyzed_at": "2026-02-15 12:05:30",
  "source_file": "result_Lotto_6-42_20241231.json",
  "game_type": "Lotto 6/42",
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-12-31"
  },
  "total_draws": 500,
  "overall_stats": { },
  "day_analysis": { },
  "top_predictions": [ ],
  "winning_predictions": [ ],
  "pattern_predictions": [ ],
  "pattern_analysis": { },
  "temporal_patterns": { },
  "historical_observations": { },
  "ultimate_predictions": [ ],
  "chart_data": { }
}
```

### Prediction Object

```json
{
  "numbers": [5, 12, 23, 34, 38, 42],
  "confidence_score": 85.5,
  "analysis": {
    "even_odd": "3E-3O",
    "high_low": "3L-3H",
    "sum": 154,
    "consecutive_pairs": 0
  },
  "prediction_type": "Ultimate Analysis"
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request (invalid input, missing fields) |
| 404 | Not Found (file/report/data not found) |
| 500 | Internal Server Error |

---

## Rate Limits

Currently, no rate limits are enforced. Recommended for production:
- Scraping: 10 requests per hour
- Analysis: 100 requests per hour
- Other endpoints: 200 requests per hour

---

## SDK Examples

### Python
```python
import requests
import time

# Scrape data
response = requests.post('http://localhost:5000/scrape', json={
    'game_type': 'Lotto 6/42',
    'start_date': '2024-01-01',
    'end_date': '2024-12-31'
})
task_id = response.json()['task_id']

# Poll progress
while True:
    progress = requests.get(f'http://localhost:5000/api/progress/{task_id}').json()
    if progress['progress']['status'] == 'completed':
        break
    time.sleep(2)

# Analyze
filename = progress['progress']['result']['filename']
analysis = requests.post('http://localhost:5000/api/analyze', json={
    'filename': filename
}).json()

# AI Analysis (optional - requires Ollama)
ai_result = requests.post('http://localhost:5000/api/ai-analyze', json={
    'filename': filename
}).json()

print(ai_result['analysis'])
```

### JavaScript
```javascript
// Scrape data
const scrapeResponse = await fetch('http://localhost:5000/scrape', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    game_type: 'Lotto 6/42',
    start_date: '2024-01-01',
    end_date: '2024-12-31'
  })
});
const { task_id } = await scrapeResponse.json();

// Poll progress
let completed = false;
while (!completed) {
  const progressResponse = await fetch(`http://localhost:5000/api/progress/${task_id}`);
  const { progress } = await progressResponse.json();

  if (progress.status === 'completed') {
    completed = true;
    const filename = progress.result.filename;

    // Analyze
    const analysisResponse = await fetch('http://localhost:5000/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename })
    });
    const analysis = await analysisResponse.json();

    // AI Analysis (optional)
    const aiResponse = await fetch('http://localhost:5000/api/ai-analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename })
    });
    const aiResult = await aiResponse.json();
  }

  await new Promise(resolve => setTimeout(resolve, 2000));
}
```

---

## Changelog

### Version 2.0.0 (Current)
- Added AI-powered analysis via Ollama (`/api/ai-analyze`)
- Added Ollama status check (`/api/ollama-status`)
- Added accuracy tracking endpoints (`/api/accuracy-*`)
- Added result integrity verification (`/api/verify-result`)
- Added game-specific result file listing (`/api/result-files`)
- Added security headers to all responses
- Added path traversal prevention with `validate_filename()`
- Added accuracy dashboard page (`/accuracy-dashboard`)
- Improved error handling with custom exception hierarchy
- Removed file-based logging (console only)
- Secured default configuration (DEBUG=False, HOST=127.0.0.1)

### Version 1.0.0
- Initial API release
- Core scraping and analysis endpoints
- Progress tracking
- Report management

### Planned Features
- Authentication and API keys
- Rate limiting
- Webhook support
- Batch operations
- Real-time WebSocket updates

---

**Last Updated:** February 16, 2026
**API Version:** 2.0.0
