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
                ├──── Accuracy Dashboard (accuracy_dashboard.html)
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
                ├──── Security Headers & Input Validation
                ├──── Scheduled Cleanup Jobs
                └──── Error Handling (Custom Exceptions)
                │
┌───────────────▼─────────────────────────────────────────────┐
│                    Business Logic Layer                      │
│                     (app/modules/)                           │
└───────────────┬─────────────────────────────────────────────┘
                │
                ├──── PCSOScraper (scraper.py)
                │     ├─ Selenium WebDriver Management
                │     ├─ PCSO Website Navigation
                │     ├─ Date Range Validation
                │     ├─ Data Extraction
                │     └─ Result Caching
                │
                ├──── LotteryAnalyzer (analyzer.py)
                │     ├─ Statistical Analysis
                │     ├─ Pattern Recognition
                │     ├─ Prediction Generation (4 algorithms)
                │     ├─ Temporal Analysis
                │     └─ Chart Data Generation
                │
                ├──── AIAnalyzer (ai_analyzer.py)
                │     ├─ Ollama Integration (LLaMA 3.1)
                │     ├─ AI-Powered Report Analysis
                │     ├─ Intelligent Number Recommendations
                │     └─ Model Status Checking
                │
                ├──── AccuracyAnalyzer (accuracy_analyzer.py)
                │     ├─ Prediction vs Actual Comparison
                │     ├─ Accuracy Scoring & Tracking
                │     ├─ Analysis Snapshot Selection
                │     └─ Provenance Tracking
                │
                └──── ProgressTracker (progress_tracker.py)
                      ├─ Task Creation & Updates
                      ├─ Atomic File Operations
                      ├─ Multi-tier Cleanup (completed/stale/old)
                      └─ Scheduled Background Cleanup
                │
┌───────────────▼─────────────────────────────────────────────┐
│                    Configuration Layer                       │
│                  (app/config.py + .env)                      │
└───────────────┬─────────────────────────────────────────────┘
                │
                ├──── Centralized Config (dataclass)
                ├──── Environment Variable Support (python-dotenv)
                ├──── Auto-generated SECRET_KEY
                ├──── Feature Flags
                └──── Validation on Init
                │
┌───────────────▼─────────────────────────────────────────────┐
│                    Custom Exceptions                         │
│                  (app/exceptions.py)                         │
└───────────────┬─────────────────────────────────────────────┘
                │
                ├──── FortuneLabException (base)
                ├──── ScraperException hierarchy
                ├──── AnalyzerException hierarchy
                ├──── DataException hierarchy
                ├──── ValidationException hierarchy
                ├──── ProgressException hierarchy
                ├──── ConfigurationException hierarchy
                └──── FileSystemException hierarchy
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
                ├──── PCSO Website (www.pcso.gov.ph)
                │     └─ Lottery result data source
                │
                └──── Ollama (localhost:11434)
                      └─ Local AI model server (LLaMA 3.1)
```

## Component Details

### 1. Flask Application Layer (`app.py`)

**Responsibilities:**
- HTTP request/response handling
- Route management
- Background task orchestration with APScheduler
- Progress tracking coordination
- Error handling with custom exception hierarchy
- Security header injection
- Path traversal prevention with `validate_filename()`
- Static file serving

**Key Routes:**

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Home page with file browser |
| `/scrape` | POST | Initiate data scraping |
| `/analyze/<filename>` | GET | Generate and display analysis |
| `/view-report/<report_filename>` | GET | View historical analysis |
| `/accuracy-dashboard` | GET | Accuracy tracking dashboard |
| `/test-chart` | GET | Chart.js test page |
| `/api/progress/<task_id>` | GET | Progress polling endpoint |
| `/api/analyze` | POST | API analysis (JSON response) |
| `/api/ai-analyze` | POST | AI-powered analysis via Ollama |
| `/api/ollama-status` | GET | Ollama service status check |
| `/api/files` | GET | List result files |
| `/api/result-files` | GET | Result files filtered by game type |
| `/api/analysis-history/<filename>` | GET | Analysis reports for a result |
| `/api/submit-actual-result` | POST | Submit actual draw for accuracy |
| `/api/delete-report/<report_filename>` | DELETE | Delete analysis report |
| `/api/export-analysis/<report_filename>` | GET | Download analysis as JSON |
| `/api/cleanup-progress` | POST | Manual progress file cleanup |
| `/api/accuracy-analysis` | GET | Get accuracy analysis data |
| `/api/accuracy-summary` | GET | Get accuracy summary |
| `/api/accuracy-provenance` | GET | Get accuracy provenance |
| `/api/verify-result` | GET | Verify result integrity |
| `/api/accuracy-files` | GET | List accuracy files |
| `/health` | GET | Health check endpoint |

**Design Patterns:**
- **Factory Pattern:** WebDriver initialization with fallback strategies
- **Observer Pattern:** Progress callbacks for scraping operations
- **Singleton Pattern:** ProgressTracker, AccuracyAnalyzer instances
- **Background Jobs:** Threading for scraping + APScheduler for cleanup
- **Strategy Pattern:** Multiple prediction algorithms

### 2. Scraper Module (`app/modules/scraper.py`)

**Class:** `PCSOScraper`

**Responsibilities:**
- WebDriver lifecycle management (setup, teardown)
- PCSO website automation
- Cross-platform ChromeDriver support
- Date range validation against available PCSO data
- Data extraction from HTML tables
- Result caching to avoid duplicate scraping
- Progress reporting via callbacks

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
[Initialize] → [Navigate] → [Validate Date Range] → [Select Dates]
    → [Select Game] → [Submit Search] → [Wait for Results]
    → [Extract Data] → [Save to JSON] → [Complete]
```

**Error Handling:**
- `DateRangeException`: When requested dates are outside PCSO's available range
- `TimeoutException`: Retry with increased wait time
- `NoSuchElementException`: Detailed logging with element info
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

### 4. AI Analyzer Module (`app/modules/ai_analyzer.py`)

**Class:** `AIAnalyzer`

**Responsibilities:**
- Integration with Ollama local AI server
- AI-powered interpretation of statistical analysis
- Intelligent number combination recommendations
- Model availability checking

**Key Methods:**
```python
__init__(model: Optional[str] = None)
    Initialize with configurable model (default: config.OLLAMA_MODEL)

check_ollama_status() -> Dict[str, Any]
    Check if Ollama is running and model is available

analyze_lottery_report(analysis_data: Dict) -> Dict[str, Any]
    Send complete analysis to AI for intelligent interpretation

_build_analysis_prompt_v2(analysis_data: Dict) -> str
    Build comprehensive prompt from all analysis data sections
```

**AI Analysis Output:**
- Executive summary of statistical findings
- Detailed statistical insights interpretation
- AI-recommended top 5 number combinations with reasoning
- Confidence assessment for each combination
- Responsible gaming disclaimer

**Configuration:**
- `OLLAMA_ENABLED`: Enable/disable AI features
- `OLLAMA_MODEL`: Model name (default: `llama3.1:8b`)
- `OLLAMA_HOST`: Ollama server URL (default: `http://localhost:11434`)
- `OLLAMA_TIMEOUT`: Request timeout in seconds (default: `120`)

### 5. Accuracy Analyzer Module (`app/modules/accuracy_analyzer.py`)

**Class:** `AccuracyAnalyzer`

**Responsibilities:**
- Compare predictions against actual draw results
- Score prediction accuracy across all 4 algorithms
- Track accuracy history over time
- Analysis snapshot selection (find most relevant pre-draw analysis)
- Provenance tracking for audit trails

**Key Methods:**
```python
analyze_accuracy(game_type, draw_date, actual_numbers, ...) -> Dict
    Compare predictions against actual results

get_accuracy_summary() -> Dict
    Aggregate accuracy across all tracked results

get_provenance(game_type, draw_date) -> Dict
    Get full audit trail for a specific accuracy check
```

### 6. Progress Tracker Module (`app/modules/progress_tracker.py`)

**Class:** `ProgressTracker`

**Responsibilities:**
- Real-time progress tracking for async operations
- Atomic file operations to prevent race conditions
- Multi-tier automatic cleanup (completed, stale, old tasks)
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

cleanup_all() -> Dict
    Multi-tier cleanup: completed (3min), stale (10min), old (24h)
```

**Cleanup Tiers:**
- **Completed tasks:** Cleaned after `CLEANUP_COMPLETED_AGE` (default: 180s)
- **Stale tasks:** Cleaned after `CLEANUP_STALE_AGE` (default: 600s)
- **Old tasks:** Cleaned after `CLEANUP_OLD_AGE` (default: 86400s)
- **Scheduled interval:** Every `CLEANUP_INTERVAL` (default: 300s) via APScheduler

### 7. Configuration Layer (`app/config.py`)

**Class:** `Config` (dataclass)

**Features:**
- Centralized configuration with environment variable support
- Auto-generated `SECRET_KEY` using `secrets.token_hex(32)` if not provided
- Secure defaults: `DEBUG=False`, `HOST=127.0.0.1`
- Directory auto-creation on initialization
- Sensitive value masking in `__repr__`
- Helper methods for scraper, log, and app configuration

**Configuration Categories:**
- Flask settings (SECRET_KEY, DEBUG, HOST, PORT)
- Data paths (DATA_PATH, ANALYSIS_PATH, PROGRESS_PATH, ACCURACY_PATH)
- Scraper settings (HEADLESS, PCSO_URL, PAGE_TIMEOUT, MAX_RETRIES)
- Progress tracking (cleanup ages and intervals)
- Logging (LOG_LEVEL - console only, no file logging)
- AI/Ollama (OLLAMA_ENABLED, OLLAMA_MODEL, OLLAMA_HOST, OLLAMA_TIMEOUT)
- Analysis (DEFAULT_PREDICTION_COUNT, CACHE_ENABLED, CACHE_TTL)
- Default date range (DEFAULT_START_YEAR/MONTH/DAY)
- Rate limiting (future feature)
- Feature flags (ENABLE_WEBSOCKET, ENABLE_API_DOCS, ENABLE_METRICS)

### 8. Custom Exceptions (`app/exceptions.py`)

**Hierarchy:**
```
FortuneLabException (base)
├── ScraperException
│   ├── WebDriverException
│   ├── PCSOWebsiteException
│   ├── DataExtractionException
│   ├── ScrapingTimeoutException
│   └── DateRangeException (with requested/available range details)
├── AnalyzerException
│   ├── InsufficientDataException
│   ├── AnalysisCalculationException
│   └── PredictionGenerationException
├── DataException
│   ├── DataNotFoundException
│   ├── InvalidDataFormatException
│   ├── DataValidationException
│   └── DataSerializationException
├── ValidationException
│   ├── InvalidGameTypeException (with valid options)
│   ├── InvalidDateRangeException
│   ├── InvalidInputException
│   └── InvalidNumbersException (with game-specific ranges)
├── ProgressException
│   ├── TaskNotFoundException
│   └── TaskAlreadyExistsException
├── ConfigurationException
│   ├── InvalidConfigurationException
│   └── MissingConfigurationException
├── FileSystemException
│   ├── FilePermissionException
│   ├── DirectoryNotFoundException
│   └── FileWriteException
├── BadRequestException (HTTP 400)
├── NotFoundException (HTTP 404)
└── InternalServerException (HTTP 500)
```

### 9. Data Layer

**Storage Format:** JSON

**Data Structure Examples:**

**Result File** (`result_*.json`):
```json
{
  "game_type": "Lotto 6/42",
  "start_date": "2024-01-01",
  "end_date": "2025-12-31",
  "total_draws": 500,
  "scraped_at": "2026-02-15 12:00:00",
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
  "analyzed_at": "2026-02-15 12:05:00",
  "source_file": "result_Lotto_6-42_20251030.json",
  "game_type": "Lotto 6/42",
  "date_range": { "start": "...", "end": "..." },
  "total_draws": 500,
  "overall_stats": { ... },
  "day_analysis": { ... },
  "top_predictions": [ ... ],
  "winning_predictions": [ ... ],
  "pattern_predictions": [ ... ],
  "pattern_analysis": { ... },
  "temporal_patterns": { ... },
  "historical_observations": { ... },
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
    ├─→ Validate inputs (game type, dates)
    ├─→ Generate task_id (UUID)
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
    ├─→ Validate date range availability
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
    ├─→ Validate filename (path traversal check)
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

### AI Analysis Flow

```
User Click "Analyze with AI"
    │
    ▼
POST /api/ai-analyze
    │
    ├─→ Validate analysis filename
    ├─→ Load analysis JSON
    ├─→ Check Ollama status
    │
    ├─→ AIAnalyzer.analyze_lottery_report()
    │   ├─→ Build comprehensive prompt (v2)
    │   │   └─→ All 8 data sections included
    │   ├─→ Send to Ollama API
    │   └─→ Return AI analysis + recommendations
    │
    └─→ Return JSON response with AI insights
```

### Accuracy Tracking Flow

```
User submits actual draw result
    │
    ▼
POST /api/submit-actual-result
    │
    ├─→ Validate inputs (game type, numbers, date)
    ├─→ Select best analysis snapshot (pre-draw)
    ├─→ Compare predictions vs actual numbers
    │   ├─→ Top predictions comparison
    │   ├─→ Winning predictions comparison
    │   ├─→ Pattern predictions comparison
    │   └─→ Ultimate predictions comparison
    ├─→ Calculate accuracy scores
    ├─→ Save accuracy report
    └─→ Return comparison results
```

## Technology Stack Details

### Backend
- **Python 3.14+**: Latest Python with improved performance
- **Flask 3.1.2**: Web framework for routing and templating
- **Selenium 4.36.0**: Browser automation for scraping
- **Pandas 2.3.3**: Data analysis and manipulation
- **NumPy 2.3.4**: Numerical computations
- **webdriver-manager 4.0.2**: Automatic ChromeDriver management
- **APScheduler 3.11.0**: Background job scheduling
- **python-dotenv 1.1.1**: Environment variable management
- **ollama 0.6.1+**: Local AI model integration

### Frontend
- **HTML5**: Semantic markup
- **CSS3**: Modern styling with CSS Grid and Flexbox
- **JavaScript (ES6+)**: Client-side interactivity
- **Chart.js**: Data visualization library
- **Fetch API**: Asynchronous HTTP requests

### Data Storage
- **JSON**: File-based storage for results and analysis
- **File System**: Organized directory structure

### External Services
- **PCSO Website**: Lottery result data source (Selenium scraping)
- **Ollama**: Local AI model server (optional, for AI analysis)

### Development Tools
- **uv**: Modern Python package manager (faster than pip)
- **Git**: Version control
- **Chrome/Chromium**: WebDriver for Selenium

## Security Architecture

### Security Headers
All responses include security headers via `@app.after_request`:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security` (production only, when DEBUG=False)

### Input Validation
- Date format validation
- Game type whitelist
- File path sanitization via `validate_filename()`
- JSON schema validation
- Number range validation (game-specific)

### Path Traversal Prevention
- `validate_filename()` strips path components and verifies resolved paths
- All user-supplied filenames checked against allowed directories
- `os.path.basename()` + `os.path.realpath()` double-check

### Output Sanitization
- Flask auto-escaping in templates
- `escapeHtml()` in JavaScript for innerHTML operations
- JSON encoding for API responses
- Generic error messages to clients (no `str(e)` exposure)

### Secret Management
- `SECRET_KEY` auto-generated with `secrets.token_hex(32)` if not set
- Sensitive values masked in config `__repr__`
- `.env` file for local secrets (not committed)

### Error Handling
- Custom exception hierarchy with HTTP status codes
- Graceful degradation
- User-friendly error messages
- Detailed logging (server-side only)
- No sensitive data exposure in API responses

## Design Patterns Used

1. **MVC (Model-View-Controller)**
   - Model: Data classes, JSON files, Config dataclass
   - View: Flask templates
   - Controller: Flask routes and business logic modules

2. **Factory Pattern**
   - WebDriver creation with multiple fallback strategies
   - Cross-platform compatibility

3. **Strategy Pattern**
   - Multiple prediction algorithms (4 types)
   - Different analysis methods

4. **Observer Pattern**
   - Progress callbacks during scraping
   - Real-time UI updates via polling

5. **Singleton Pattern**
   - ProgressTracker, AccuracyAnalyzer instances
   - Flask application instance
   - Config instance

6. **Template Method Pattern**
   - Base analysis workflow
   - Customizable prediction generation

## Performance Considerations

### Caching Strategy
1. **Result Caching**: Don't re-scrape if file exists
2. **Progress Cleanup**: Multi-tier auto-removal (3min/10min/24h)
3. **Analysis Reports**: Saved for historical reference
4. **Scheduled Cleanup**: APScheduler runs every 5 minutes

### Optimization Points
1. **Lazy Loading**: Load data only when needed
2. **Background Jobs**: Non-blocking scraping operations
3. **Efficient Algorithms**: O(n) or better for analysis
4. **Console-only Logging**: Removed file-based log rotation for simplicity

### Scalability
- Current: ~10,000 draws per game (manageable with JSON)
- Future: Consider SQLite for >100MB datasets
- AI Analysis: Requires local Ollama server with sufficient RAM

## Monitoring & Logging

### Logging Configuration
- Console-only logging (no file rotation)
- Configurable via `LOG_LEVEL` environment variable
- Third-party loggers suppressed (selenium, urllib3)

### Log Structure
```python
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
```

### Health Monitoring
- `/health` endpoint for status checks
- `/api/ollama-status` for AI service monitoring
- Returns JSON with timestamp and status

## Deployment Architecture

### Development
```
Local Machine
├─ Python 3.14+
├─ Chrome Browser
├─ uv package manager
├─ Ollama (optional, for AI features)
└─ Flask dev server (localhost:5000)
```

### Production (Future)
```
Cloud Server
├─ Python 3.14+
├─ Chrome/Chromium (headless)
├─ Gunicorn/uWSGI (WSGI server)
├─ Nginx (reverse proxy)
├─ SSL/TLS certificate
├─ Ollama (for AI features)
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

### Adding New AI Models
1. Pull model via `ollama pull <model-name>`
2. Update `OLLAMA_MODEL` in `.env`
3. No code changes needed (model is configurable)

### Adding New Visualizations
1. Prepare data in `get_chart_data()`
2. Add Chart.js configuration in template
3. Style with CSS
4. Add interactivity with JavaScript

---

**Last Updated:** February 16, 2026
**Version:** 2.0.0
