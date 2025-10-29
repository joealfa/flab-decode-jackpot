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
  "details": { ... }  // Optional
}
```

---

## Web Routes

### 1. Home Page

**Endpoint:** `GET /`

**Description:** Main landing page with result file browser

**Response:** HTML page

**Template:** `index.html`

**Data Provided:**
- `result_files`: List of available result files with metadata

---

### 2. Dashboard

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

### 4. Test Chart

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
  "end_date": "2025-10-30"
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

**Error Response (400):**
```json
{
  "success": false,
  "error": "Start date must be before end date"
}
```

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
    "total_draws": 500,
    // ... complete lottery data
  },
  "overall_stats": {
    "total_draws": 500,
    "most_frequent_numbers": [[5, 120], [12, 115], ...],
    "hot_numbers": [5, 12, 23, 34, 38, 42],
    // ... more statistics
  },
  "day_analysis": {
    "Monday": { ... },
    "Tuesday": { ... },
    // ... all days
  },
  "top_predictions": [
    {
      "numbers": [5, 12, 23, 34, 38, 42],
      "confidence_score": 85.5,
      "analysis": {
        "even_odd": "3E-3O",
        "high_low": "3L-3H",
        "sum": 154,
        "consecutive_pairs": 0
      }
    },
    // ... more predictions
  ],
  "winning_predictions": [ ... ],
  "chart_data": { ... }
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": "Filename is required"
}
```

**Error Response (404):**
```json
{
  "success": false,
  "error": "Result file not found"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "result_Lotto_6-42_20251030.json"
  }'
```

---

### 4. List Result Files

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
      "scraped_at": "2025-10-30 12:00:00"
    },
    // ... more files
  ]
}
```

**Example:**
```bash
curl http://localhost:5000/api/files
```

---

### 5. Get Analysis History

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
      "filename": "analysis_result_Lotto_6-42_20251030_20251030_120530.json",
      "analyzed_at": "2025-10-30 12:05:30",
      "created_at": "2025-10-30 12:05:30",
      "size": 524288
    },
    // ... more reports
  ],
  "count": 5
}
```

**Example:**
```bash
curl http://localhost:5000/api/analysis-history/result_Lotto_6-42_20251030.json
```

---

### 6. Submit Actual Result

**Endpoint:** `POST /api/submit-actual-result`

**Description:** Submit actual draw result for accuracy tracking

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "game_type": "Lotto 6/42",
  "draw_date": "2025-10-30",
  "numbers": [5, 12, 23, 34, 38, 42],
  "jackpot": "₱50,000,000",
  "winners": "2"
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

**Success Response (200):**
```json
{
  "success": true,
  "message": "Actual result added successfully",
  "accuracy_results": {
    "actual_numbers": [5, 12, 23, 34, 38, 42],
    "draw_date": "2025-10-30",
    "game_type": "Lotto 6/42",
    "top_predictions_comparison": [
      {
        "rank": 1,
        "predicted_numbers": [5, 12, 23, 34, 38, 40],
        "matches": 5,
        "confidence_score": 85.5
      },
      // ... more comparisons
    ],
    "winning_predictions_comparison": [ ... ],
    "pattern_predictions_comparison": [ ... ]
  },
  "result_file": "result_Lotto_6-42_20251030.json",
  "total_draws": 501
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": "Numbers must be an array of 6 integers"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/submit-actual-result \
  -H "Content-Type: application/json" \
  -d '{
    "game_type": "Lotto 6/42",
    "draw_date": "2025-10-30",
    "numbers": [5, 12, 23, 34, 38, 42],
    "jackpot": "₱50,000,000",
    "winners": "2"
  }'
```

---

### 7. Delete Analysis Report

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

**Error Response (404):**
```json
{
  "success": false,
  "error": "Report not found"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:5000/api/delete-report/analysis_result_Lotto_6-42_20251030_20251030_120530.json
```

---

### 8. Export Analysis Report

**Endpoint:** `GET /api/export-analysis/<report_filename>`

**Description:** Export analysis report as downloadable JSON

**Parameters:**
- `report_filename` (path): Name of the analysis report file

**Success Response (200):**
- Content-Type: `application/json`
- Content-Disposition: `attachment; filename=<report_filename>`
- Body: Complete analysis report JSON

**Error Response (404):**
```json
{
  "success": false,
  "error": "Report not found"
}
```

**Example:**
```bash
curl -O -J http://localhost:5000/api/export-analysis/analysis_result_Lotto_6-42_20251030_20251030_120530.json
```

---

### 9. Cleanup Progress Files

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

**Example:**
```bash
curl -X POST http://localhost:5000/api/cleanup-progress \
  -H "Content-Type: application/json" \
  -d '{"max_age_seconds": 600}'
```

---

### 10. Health Check

**Endpoint:** `GET /health`

**Description:** Application health check endpoint

**Success Response (200):**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-30T12:00:00.000000"
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
  "scraped_at": "2025-10-30 12:00:00",
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
  "analyzed_at": "2025-10-30 12:05:30",
  "source_file": "result_Lotto_6-42_20241231.json",
  "game_type": "Lotto 6/42",
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-12-31"
  },
  "total_draws": 500,
  "overall_stats": { /* Overall Statistics */ },
  "day_analysis": { /* Day-specific Analysis */ },
  "top_predictions": [ /* Top Predictions */ ],
  "winning_predictions": [ /* Winner-optimized Predictions */ ],
  "pattern_predictions": [ /* Pattern-based Predictions */ ],
  "pattern_analysis": { /* Consecutive Pattern Analysis */ },
  "temporal_patterns": { /* Temporal Analysis */ },
  "historical_observations": { /* Historical Insights */ },
  "ultimate_predictions": [ /* Ultimate Predictions */ ],
  "chart_data": { /* Chart Visualization Data */ }
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
| 400 | Bad Request (invalid input) |
| 404 | Not Found (file/report not found) |
| 500 | Internal Server Error |

---

## Rate Limits

Currently, no rate limits are enforced. Recommended for production:
- Scraping: 10 requests per hour
- Analysis: 100 requests per hour
- Other endpoints: 200 requests per hour

---

## Webhooks (Future)

Planned webhook support for:
- Scraping completion
- Analysis completion
- New draw results

---

## SDK Examples

### Python
```python
import requests

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
analysis = requests.post('http://localhost:5000/api/analyze', json={
    'filename': progress['progress']['result']['filename']
}).json()

print(analysis['top_predictions'])
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
    
    // Analyze
    const analysisResponse = await fetch('http://localhost:5000/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: progress.result.filename })
    });
    const analysis = await analysisResponse.json();
    console.log(analysis.top_predictions);
  }
  
  await new Promise(resolve => setTimeout(resolve, 2000));
}
```

---

## Changelog

### Version 1.0.0 (Current)
- Initial API release
- Core scraping and analysis endpoints
- Progress tracking
- Report management

### Planned Features
- Authentication and API keys
- Rate limiting
- Webhook support
- Batch operations
- Advanced filtering and search
- Real-time WebSocket updates

---

**Last Updated:** October 30, 2025  
**API Version:** 1.0.0
