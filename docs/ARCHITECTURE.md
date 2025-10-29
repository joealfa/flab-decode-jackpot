# Fortune Lab: Architecture Documentation

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
│              (Flask Templates + JavaScript)                  │
└───────────────┬─────────────────────────────────────────────┘
                │
                ├──── Home Page (index.html)
                ├──── Dashboard (dashboard.html)
                └──── API Endpoints (JSON)
                │
┌───────────────▼─────────────────────────────────────────────┐
│                     Flask Application                        │
│                        (app.py)                              │
└───────────────┬─────────────────────────────────────────────┘
                │
                ├──── Routes & Request Handling
                ├──── Background Task Management
                ├──── Progress Tracking
                └──── Error Handling
                │
┌───────────────▼─────────────────────────────────────────────┐
│                    Business Logic Layer                      │
│                     (app/modules/)                           │
└───────────────┬─────────────────────────────────────────────┘
                │
                ├──── PCSOScraper (scraper.py)
                │     ├─ Selenium WebDriver Management
                │     ├─ PCSO Website Navigation
                │     ├─ Data Extraction
                │     └─ Result Caching
                │
                ├──── LotteryAnalyzer (analyzer.py)
                │     ├─ Statistical Analysis
                │     ├─ Pattern Recognition
                │     ├─ Prediction Generation
                │     ├─ Temporal Analysis
                │     └─ Chart Data Generation
                │
                └──── ProgressTracker (progress_tracker.py)
                      ├─ Task Creation
                      ├─ Progress Updates
                      ├─ Atomic File Operations
                      └─ Cleanup Management
                │
┌───────────────▼─────────────────────────────────────────────┐
│                      Data Layer                              │
│                    (app/data/)                               │
└───────────────┬─────────────────────────────────────────────┘
                │
                ├──── result_*.json (Scraped lottery data)
                ├──── analysis/*.json (Analysis reports)
                ├──── progress/*.json (Progress tracking)
                └──── accuracy/*.json (Validation results)
                │
┌───────────────▼─────────────────────────────────────────────┐
│                  External Services                           │
└─────────────────────────────────────────────────────────────┘
                │
                └──── PCSO Website (www.pcso.gov.ph)
                      └─ Lottery result data source
```

## Component Details

### 1. Flask Application Layer (`app.py`)

**Responsibilities:**
- HTTP request/response handling
- Route management
- Background task orchestration
- Progress tracking coordination
- Error handling and logging
- Static file serving

**Key Routes:**
- `GET /` - Home page with file browser
- `POST /scrape` - Initiate data scraping
- `GET /analyze/<filename>` - Generate and display analysis
- `GET /api/progress/<task_id>` - Progress polling endpoint
- `POST /api/submit-actual-result` - Add actual draw results
- `GET /view-report/<report_filename>` - View historical analysis
- `GET /health` - Health check endpoint

**Design Patterns:**
- **Factory Pattern:** WebDriver initialization with fallback strategies
- **Observer Pattern:** Progress callbacks for scraping operations
- **Singleton Pattern:** ProgressTracker instance
- **Background Jobs:** Threading for long-running scraping tasks

### 2. Scraper Module (`app/modules/scraper.py`)

**Class:** `PCSOScraper`

**Responsibilities:**
- WebDriver lifecycle management (setup, teardown)
- PCSO website automation
- Cross-platform ChromeDriver support
- Data extraction from HTML tables
- Result caching to avoid duplicate scraping
- Progress reporting

**Key Methods:**
```python
__init__(headless: bool = True)
    Initialize scraper with headless option

scrape_lottery_data(game_type, start_date, end_date, save_path, progress_callback, scraping_progress_callback) -> Dict
    Main scraping orchestrator
    
_setup_driver() -> webdriver.Chrome
    Cross-platform WebDriver initialization
    
_select_date(month, day, year, prefix)
    PCSO form date selection
    
_extract_results(progress_callback) -> List[Dict]
    HTML table parsing and extraction
    
_save_results(data, game_type, end_date, save_path) -> str
    JSON file saving with naming convention
```

**State Machine:**
```
[Initialize] → [Navigate] → [Select Dates] → [Select Game] 
    → [Submit Search] → [Wait for Results] → [Extract Data] 
    → [Save to JSON] → [Complete]
```

**Error Handling:**
- TimeoutException: Retry with increased wait time
- NoSuchElementException: Detailed logging with element info
- Platform-specific: Multiple fallback strategies for driver

### 3. Analyzer Module (`app/modules/analyzer.py`)

**Class:** `LotteryAnalyzer`

**Responsibilities:**
- Statistical analysis of lottery data
- Pattern recognition and trend analysis
- Multiple prediction algorithm implementations
- Temporal pattern analysis
- Chart data preparation
- Historical observation generation

**Analysis Components:**

1. **Overall Statistics**
   - Number frequency distribution
   - Hot/cold number identification
   - Even/odd pattern analysis
   - High/low distribution
   - Consecutive number patterns
   - Sum range analysis

2. **Day-Specific Analysis**
   - Per-weekday pattern analysis
   - Day-specific hot numbers
   - Customized predictions per day

3. **Winner Analysis**
   - Winner draw pattern identification
   - Winning number frequency
   - Temporal win patterns
   - Jackpot statistics
   - Win probability estimation

4. **Consecutive Draw Patterns**
   - Number carryover analysis
   - Pattern transition tracking
   - Sum difference trends
   - Predictive modeling based on sequences

5. **Temporal Patterns**
   - Year-over-year trends
   - Monthly patterns
   - Weekly patterns
   - Consistency scoring
   - Time-based number performance

**Prediction Algorithms:**

1. **Top Predictions** (`generate_top_predictions`)
   - Weighted frequency-based selection
   - Balance optimization (even/odd, high/low)
   - Spread maximization

2. **Winning Predictions** (`generate_winning_predictions`)
   - Optimized for winner draw patterns
   - Enhanced scoring for historical winners
   - Pattern matching with successful draws

3. **Pattern-Based** (`generate_pattern_based_prediction`)
   - Consecutive draw pattern analysis
   - Carryover number prediction
   - Recent trend integration

4. **Ultimate Predictions** (`generate_ultimate_predictions`)
   - Multi-dimensional scoring:
     * Frequency score (30%)
     * Temporal consistency (25%)
     * Recent performance (20%)
     * Winner optimization (15%)
     * Pattern matching (10%)
   - Comprehensive analysis combination
   - Randomness acknowledgment

### 4. Progress Tracker Module (`app/modules/progress_tracker.py`)

**Class:** `ProgressTracker`

**Responsibilities:**
- Real-time progress tracking for async operations
- Atomic file operations to prevent race conditions
- Automatic cleanup of old progress files
- Status management (started, in-progress, completed, failed)

**Key Methods:**
```python
create_task(task_id: str)
    Initialize new progress tracking

update_progress(task_id, current, total, message)
    Update progress with atomic writes

get_progress(task_id) -> Optional[Dict]
    Retrieve progress with retry logic

complete_task(task_id, message)
    Mark task as completed

fail_task(task_id, error_message)
    Mark task as failed

cleanup_completed_tasks(max_age_seconds) -> int
    Remove old completed tasks
```

**Race Condition Prevention:**
- Temp file creation + atomic rename (`os.replace`)
- Retry logic with exponential backoff
- JSON parsing error handling

### 5. Data Layer

**Storage Format:** JSON

**Data Structure Examples:**

**Result File** (`result_*.json`):
```json
{
  "game_type": "Lotto 6/42",
  "start_date": "2015-01-01",
  "end_date": "2025-10-30",
  "total_draws": 500,
  "scraped_at": "2025-10-30 12:00:00",
  "results": [
    {
      "game": "Lotto 6/42",
      "date": "10/30/2025",
      "day_of_week": "Thursday",
      "numbers": [5, 12, 23, 34, 38, 42],
      "jackpot": "₱50,000,000",
      "winners": "2"
    }
  ]
}
```

**Analysis Report** (`analysis_*.json`):
```json
{
  "analyzed_at": "2025-10-30 12:05:00",
  "source_file": "result_Lotto_6-42_20251030.json",
  "overall_stats": { ... },
  "day_analysis": { ... },
  "top_predictions": [ ... ],
  "winning_predictions": [ ... ],
  "pattern_predictions": [ ... ],
  "temporal_patterns": { ... },
  "ultimate_predictions": [ ... ],
  "chart_data": { ... }
}
```

**Progress File** (`<task_id>.json`):
```json
{
  "task_id": "uuid-string",
  "status": "in-progress",
  "current": 250,
  "total": 500,
  "percentage": 50,
  "message": "Extracting results: 250/500 rows...",
  "started_at": 1698765432.123,
  "updated_at": 1698765450.456
}
```

## Data Flow Diagrams

### Scraping Flow

```
User Input
    │
    ├─→ Game Type
    ├─→ Start Date
    └─→ End Date
    │
    ▼
Flask Route (/scrape)
    │
    ├─→ Validate inputs
    ├─→ Generate task_id
    └─→ Start background thread
    │
    ▼
Background Thread
    │
    ├─→ Create progress task
    ├─→ Check cache (existing file?)
    │   ├─→ YES: Load from cache
    │   └─→ NO: Continue scraping
    │
    ├─→ Initialize PCSOScraper
    ├─→ Setup WebDriver
    ├─→ Navigate to PCSO
    ├─→ Fill date selectors
    ├─→ Select game type
    ├─→ Click search
    ├─→ Wait for results
    ├─→ Extract table data
    │   └─→ Report progress per row
    ├─→ Save to JSON
    └─→ Complete progress task
    │
    ▼
Client Polling (/api/progress/<task_id>)
    │
    ├─→ Read progress JSON
    ├─→ Return status to UI
    └─→ Update progress bar
```

### Analysis Flow

```
User Click "Analyze"
    │
    ▼
Flask Route (/analyze/<filename>)
    │
    ├─→ Load result JSON file
    ├─→ Create LotteryAnalyzer instance
    │
    ├─→ Calculate overall statistics
    ├─→ Analyze all days
    ├─→ Generate predictions (4 types)
    ├─→ Analyze patterns
    ├─→ Temporal analysis
    ├─→ Historical observations
    ├─→ Chart data preparation
    │
    ├─→ Save analysis report
    └─→ Render dashboard template
    │
    ▼
Dashboard Display
    │
    ├─→ Statistics cards
    ├─→ Prediction tables
    ├─→ Pattern visualizations
    └─→ Interactive charts (Chart.js)
```

## Technology Stack Details

### Backend
- **Python 3.14+**: Latest Python with improved performance
- **Flask 3.1.2**: Web framework for routing and templating
- **Selenium 4.36.0**: Browser automation for scraping
- **Pandas 2.3.3**: Data analysis and manipulation
- **NumPy 2.3.4**: Numerical computations
- **webdriver-manager 4.0.2**: Automatic ChromeDriver management

### Frontend
- **HTML5**: Semantic markup
- **CSS3**: Modern styling with CSS Grid and Flexbox
- **JavaScript (ES6+)**: Client-side interactivity
- **Chart.js**: Data visualization library
- **Fetch API**: Asynchronous HTTP requests

### Data Storage
- **JSON**: File-based storage for results and analysis
- **File System**: Organized directory structure

### Development Tools
- **uv**: Modern Python package manager (faster than pip)
- **Git**: Version control
- **Chrome/Chromium**: WebDriver for Selenium

## Design Patterns Used

1. **MVC (Model-View-Controller)**
   - Model: Data classes and JSON files
   - View: Flask templates
   - Controller: Flask routes and business logic

2. **Factory Pattern**
   - WebDriver creation with multiple fallback strategies
   - Cross-platform compatibility

3. **Strategy Pattern**
   - Multiple prediction algorithms
   - Different analysis methods

4. **Observer Pattern**
   - Progress callbacks during scraping
   - Real-time UI updates via polling

5. **Singleton Pattern**
   - ProgressTracker instance
   - Flask application instance

6. **Template Method Pattern**
   - Base analysis workflow
   - Customizable prediction generation

## Security Architecture

### Input Validation
- Date format validation
- Game type whitelist
- File path sanitization
- JSON schema validation

### Output Sanitization
- Flask auto-escaping in templates
- JSON encoding for API responses
- Safe file path generation

### File Access Control
- Restricted to `app/data/` directory
- No arbitrary file access
- Path traversal prevention

### Error Handling
- Graceful degradation
- User-friendly error messages
- Detailed logging (server-side only)
- No sensitive data exposure

## Performance Considerations

### Caching Strategy
1. **Result Caching**: Don't re-scrape if file exists
2. **Progress Cleanup**: Auto-remove old progress files
3. **Analysis Reports**: Save for historical reference

### Optimization Points
1. **Lazy Loading**: Load data only when needed
2. **Pagination**: For large result sets (future)
3. **Background Jobs**: Non-blocking scraping operations
4. **Efficient Algorithms**: O(n) or better for analysis

### Scalability
- Current: ~10,000 draws per game (manageable with JSON)
- Future: Consider SQLite for >100MB datasets
- Horizontal scaling: Not needed for single-user application
- Vertical scaling: CPU-bound (analysis), I/O-bound (scraping)

## Monitoring & Logging

### Logging Levels
- **INFO**: Normal operations (scraping started, analysis complete)
- **WARNING**: Recoverable issues (file exists, using cache)
- **ERROR**: Failures (scraping failed, analysis error)
- **DEBUG**: Detailed diagnostics (element selection, data parsing)

### Log Structure
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Health Monitoring
- `/health` endpoint for status checks
- Returns JSON with timestamp and status
- Can be extended with system metrics

## Deployment Architecture

### Development
```
Local Machine
├─ Python 3.14+
├─ Chrome Browser
├─ uv package manager
└─ Flask dev server (localhost:5000)
```

### Production (Future)
```
Cloud Server (e.g., DigitalOcean, AWS, Heroku)
├─ Python 3.14+
├─ Chrome/Chromium (headless)
├─ Gunicorn/uWSGI (WSGI server)
├─ Nginx (reverse proxy)
├─ SSL/TLS certificate
└─ Environment variables for config
```

## Extension Points

### Adding New Game Types
1. Update `GAME_TYPES` in `scraper.py`
2. Test scraping with new game
3. Verify analysis works with different number ranges

### Adding New Analysis Methods
1. Add method to `LotteryAnalyzer` class
2. Update `analyze()` route to include new analysis
3. Create template section for display
4. Add chart if needed

### Adding New Visualizations
1. Prepare data in `get_chart_data()`
2. Add Chart.js configuration in template
3. Style with CSS
4. Add interactivity with JavaScript

### API Integration
1. Create `/api/v1/` route prefix
2. Implement authentication (API keys)
3. Add rate limiting
4. Document with OpenAPI/Swagger

---

**Last Updated:** October 30, 2025  
**Version:** 1.0.0
