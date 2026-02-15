# AI Assistant Instructions for Fortune Lab: Decoding the Jackpot

## Project Overview

**Project Name:** Fortune Lab: Decoding the Jackpot
**Purpose:** Philippine PCSO lottery analysis application with data scraping, statistical analysis, AI-powered insights, and probability-based predictions
**Tech Stack:** Python 3.14+, Flask, Selenium, Pandas, NumPy, Ollama
**Package Manager:** `uv` (NOT pip - this is critical!)

## Core Principles

### 1. **Always Use `uv` for Package Management**
- Correct: `uv add package-name`, `uv sync`, `uv run python script.py`
- Wrong: `pip install`, `python -m pip install`
- When adding dependencies, ALWAYS use `uv add` to update `pyproject.toml`

### 2. **Maintain Modular Architecture**
The project follows a clean separation of concerns:
```
app/
├── config.py             # Centralized configuration (dataclass)
├── exceptions.py         # Custom exception hierarchy
├── modules/              # Core business logic
│   ├── scraper.py        # Web scraping (Selenium)
│   ├── analyzer.py       # Statistical analysis
│   ├── ai_analyzer.py    # AI-powered analysis (Ollama)
│   ├── accuracy_analyzer.py  # Prediction accuracy tracking
│   └── progress_tracker.py   # Progress tracking
├── templates/            # Flask HTML templates
├── static/               # CSS, JavaScript, assets
└── data/                 # JSON data storage
    ├── result_*.json         # Scraped lottery results
    ├── analysis/             # Analysis reports
    ├── progress/             # Progress tracking files
    └── accuracy/             # Accuracy validation
```

### 3. **Data Flow Understanding**
1. **Scraping:** User selects game type + date range -> Selenium scrapes PCSO website -> Saves to `data/result_*.json`
2. **Analysis:** Load result file -> LotteryAnalyzer processes -> Generate predictions (4 algorithms) -> Save to `data/analysis/`
3. **AI Analysis:** Load analysis report -> AIAnalyzer sends to Ollama -> Returns AI interpretation + recommendations
4. **Accuracy Tracking:** Submit actual draw -> Compare against predictions -> Save to `data/accuracy/`
5. **Display:** Flask routes serve templates with analysis data -> JavaScript renders charts

### 4. **Supported Lottery Games**
- Lotto 6/42
- Mega Lotto 6/45
- Super Lotto 6/49
- Grand Lotto 6/55
- Ultra Lotto 6/58

Format: `{game_name} {numbers_to_pick}/{max_number}`

## Development Guidelines

### Python Code Standards

1. **Type Hints:** Use type hints for function parameters and return values
   ```python
   def analyze_data(self, data: Dict) -> Dict:
       ...
   ```

2. **Docstrings:** Use Google-style docstrings
   ```python
   """
   Brief description.

   Args:
       param1: Description
       param2: Description

   Returns:
       Description of return value
   """
   ```

3. **Error Handling:** Use custom exceptions from `app/exceptions.py`
   ```python
   from app.exceptions import DataNotFoundException, BadRequestException

   if not os.path.exists(filepath):
       raise DataNotFoundException(f"File not found: {filepath}")
   ```

4. **Logging:** Use the logging module, not print statements
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.info("Process started")
   logger.error("Error occurred", exc_info=True)
   ```

5. **Configuration:** Always use the centralized config
   ```python
   from app.config import config

   data_path = config.DATA_PATH
   headless = config.HEADLESS
   ```

### Flask Development

1. **Route Organization:** Keep routes focused and single-purpose
   - Use `/api/*` for JSON endpoints
   - Use regular routes for page rendering

2. **Error Handling:** Use custom exceptions with `build_error_response()`
   ```python
   try:
       # logic
   except BadRequestException as e:
       return build_error_response(e, 400)
   except DataNotFoundException as e:
       return build_error_response(e, 404)
   except Exception as e:
       logger.error(f"Error: {str(e)}", exc_info=True)
       error = InternalServerException("Operation failed")
       return build_error_response(error, 500)
   ```

3. **JSON Serialization:** Handle NumPy types before returning JSON
   ```python
   data = convert_to_serializable(data)
   return jsonify(data)
   ```

4. **Background Tasks:** Use threading for long-running operations (scraping)
   - Return task_id immediately
   - Provide progress endpoint for polling

5. **Input Validation:** Always validate filenames with `validate_filename()`
   ```python
   filepath = validate_filename(filename, config.DATA_PATH)
   ```

### Security Rules

1. **Path Traversal:** Always use `validate_filename()` for user-supplied filenames
2. **XSS Prevention:** Use `escapeHtml()` in JavaScript when inserting into `innerHTML`
3. **Error Responses:** Never expose `str(e)` to clients; log details server-side, return generic messages
4. **No `alert()`:** Use `showAlert(message, type)` instead of browser `alert()`
5. **No `console.log()`:** Remove before committing; use only during active debugging
6. **Security Headers:** Applied automatically via `@app.after_request`

### Data Processing Rules

1. **NumPy/Pandas Conversions:** Always convert to native Python types before JSON serialization
   ```python
   value = int(numpy_value)
   value = float(numpy_value)
   value = numpy_array.tolist()
   ```

2. **Date Handling:**
   - Input format: `YYYY-MM-DD` (ISO 8601)
   - PCSO format: `MM/DD/YYYY`
   - Always convert consistently

3. **File Naming Convention:**
   - Results: `result_{game_slug}_{end_date_YYYYMMDD}.json`
   - Analysis: `analysis_{result_base_name}_{timestamp_YYYYMMDD_HHMMSS}.json`
   - Accuracy: `accuracy_{game_slug}_{timestamp}.json`

### Selenium/Scraping Guidelines

1. **Headless Mode:** Default to headless=True for production
2. **Cross-Platform:** Support Windows, Linux, macOS
3. **Error Recovery:** Handle timeouts gracefully
4. **Date Range Validation:** Validates against PCSO available date range before scraping
5. **Caching:** Check if file exists before scraping (avoid duplicate work)
6. **Progress Reporting:** Use callbacks to report progress

### Analysis Guidelines

1. **Probability Disclaimer:** Always acknowledge that lottery draws are random
2. **Multiple Prediction Methods:**
   - `generate_top_predictions()` - Frequency-based
   - `generate_winning_predictions()` - Winner-optimized
   - `generate_pattern_based_prediction()` - Pattern-based
   - `generate_ultimate_predictions()` - Comprehensive multi-dimensional

3. **Statistical Integrity:**
   - Use appropriate statistical measures
   - Validate data before analysis
   - Handle edge cases (empty datasets, etc.)

### AI Analysis Guidelines

1. **Ollama Integration:** Uses local Ollama server (no data sent externally)
2. **Configuration:** Model, host, timeout all configurable via environment variables
3. **Error Handling:** Check Ollama status before attempting analysis
4. **Prompt Engineering:** Use comprehensive prompts including all 8 data sections
5. **Model Flexibility:** Supports any Ollama-compatible model

## Common Tasks & Solutions

### Adding a New Dependency
```bash
uv add package-name
uv sync
```

### Running the Application
```bash
# Development
uv run python app.py

# Or
uv run flask run
```

### Setting Up AI Features
```bash
# Install and start Ollama
ollama serve

# Pull the model
ollama pull llama3.1:8b

# Configure in .env
OLLAMA_ENABLED=True
OLLAMA_MODEL=llama3.1:8b
```

### Debugging
```python
# Enable debug logging
LOG_LEVEL=DEBUG in .env

# Flask debug mode
DEBUG=True in .env
```

### Adding New Analysis Features

1. Add method to `LotteryAnalyzer` class in `app/modules/analyzer.py`
2. Update `analyze()` route in `app.py` to include new analysis
3. Update `dashboard.html` template to display results
4. Add JavaScript for charts if needed in `static/js/main.js`

### Creating New API Endpoints

```python
@app.route('/api/new-endpoint', methods=['POST'])
def new_endpoint():
    try:
        data = request.get_json()
        # Process data
        result = process_data(data)
        return jsonify({'success': True, 'data': result})
    except BadRequestException as e:
        return build_error_response(e, 400)
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        error = InternalServerException("Operation failed")
        return build_error_response(error, 500)
```

## Critical Gotchas & Solutions

### 1. Python 3.14 RC2 SSL Warning
**Issue:** SSL errors when closing WebDriver
**Solution:** Ignore in cleanup, already handled in code

### 2. NumPy JSON Serialization
**Issue:** `TypeError: Object of type 'int64' is not JSON serializable`
**Solution:** Use `convert_to_serializable()` function before `jsonify()`

### 3. Progress File Race Conditions
**Issue:** Concurrent reads/writes to progress JSON
**Solution:** Use atomic writes with temp files (already implemented in `progress_tracker.py`)

### 4. Empty Result Sets
**Issue:** Division by zero in analysis
**Solution:** Always check `if not results:` before calculations

### 5. ChromeDriver Platform Issues
**Issue:** Different paths on different OS
**Solution:** Multi-strategy driver setup (already implemented in `scraper.py`)

### 6. Date Range Validation
**Issue:** Requesting dates outside PCSO available range
**Solution:** Scraper validates against PCSO dropdown values; raises `DateRangeException`

### 7. Secret Key Security
**Issue:** Hardcoded secret key in production
**Solution:** Auto-generated with `secrets.token_hex(32)` if not set in environment

## Testing Checklist

Before committing changes, verify:

- [ ] Code runs without errors: `uv run python app.py`
- [ ] All dependencies in `pyproject.toml`
- [ ] Type hints added for new functions
- [ ] Docstrings added for new functions
- [ ] Custom exceptions used (not generic `Exception` for known error cases)
- [ ] Logging added (no print statements)
- [ ] NumPy types converted before JSON serialization
- [ ] Cross-platform compatibility considered
- [ ] `validate_filename()` used for user-supplied filenames
- [ ] `escapeHtml()` used in JavaScript for innerHTML
- [ ] No `str(e)` exposed in API responses
- [ ] UI responsive and accessible
- [ ] JavaScript errors checked in browser console
- [ ] No `console.log()` left in committed code
- [ ] No `alert()` calls in JavaScript

## File Modification Guidelines

### When Modifying `scraper.py`
- Test on multiple platforms if changing driver setup
- Update progress callbacks if adding steps
- Maintain backward compatibility with existing data format
- Test with different date ranges
- Handle `DateRangeException` for out-of-range dates

### When Modifying `analyzer.py`
- Ensure all return values are JSON-serializable
- Test with empty datasets
- Validate statistical calculations
- Update `get_chart_data()` if adding visualizations

### When Modifying `ai_analyzer.py`
- Test with Ollama running and not running
- Handle model availability checks
- Keep prompts comprehensive but not too long
- Test with different analysis data structures

### When Modifying `app.py`
- Keep routes RESTful
- Use custom exceptions with `build_error_response()`
- Use `validate_filename()` for file operations
- Update API documentation if adding endpoints
- Test with concurrent requests

### When Modifying Templates
- Maintain consistent styling (use existing CSS classes)
- Ensure responsive design (mobile-friendly)
- Use `escapeHtml()` for any user/server data in innerHTML
- Use `showAlert()` instead of `alert()`
- Test JavaScript in multiple browsers
- Use Chart.js for visualizations (already included)

## Application Routes

### Web Pages
- Home: `/`
- Analyze: `/analyze/<filename>`
- View Report: `/view-report/<report_filename>`
- Accuracy Dashboard: `/accuracy-dashboard`
- Test Chart: `/test-chart`
- Health: `/health`

### API Endpoints
- `POST /scrape` - Initiate scraping
- `GET /api/progress/<task_id>` - Check progress
- `POST /api/analyze` - API analysis
- `POST /api/ai-analyze` - AI-powered analysis
- `GET /api/ollama-status` - Ollama status
- `GET /api/files` - List result files
- `GET /api/result-files` - Result files by game type
- `GET /api/analysis-history/<filename>` - Analysis history
- `POST /api/submit-actual-result` - Submit draw result
- `DELETE /api/delete-report/<filename>` - Delete report
- `GET /api/export-analysis/<filename>` - Export report
- `POST /api/cleanup-progress` - Cleanup progress files
- `GET /api/accuracy-analysis` - Accuracy analysis
- `GET /api/accuracy-summary` - Accuracy summary
- `GET /api/accuracy-provenance` - Accuracy provenance
- `GET /api/verify-result` - Verify result integrity
- `GET /api/accuracy-files` - List accuracy files

## Version Control

### Commit Message Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: feat, fix, docs, style, refactor, test, chore

Examples:
- `feat(analyzer): add temporal pattern analysis`
- `fix(scraper): handle ChromeDriver platform issues`
- `docs: update AI instructions with testing guidelines`

## Security Considerations

1. **Input Validation:** Always validate user inputs (dates, game types, filenames)
2. **File Access:** Use `validate_filename()` to restrict access to data directories
3. **XSS Prevention:** Use Flask auto-escaping + `escapeHtml()` in JavaScript
4. **Error Masking:** Never expose internal errors to clients
5. **Security Headers:** Applied via `@app.after_request` middleware
6. **Secret Management:** Use environment variables, auto-generate if not set
7. **HSTS:** Enabled in production (when DEBUG=False)

## Future Enhancements (Ideas)

- User authentication and saved preferences
- Rate limiting implementation
- WebSocket for real-time progress updates
- PDF report generation
- Dark mode
- Multi-language support
- Mobile app (React Native/Flutter)
- Email notifications for new draws
- REST API with API keys

---

**Remember:** This is an educational and entertainment application. Always include disclaimers about lottery randomness and responsible gaming.
