# AI Assistant Instructions for Fortune Lab: Decoding the Jackpot

## Project Overview

**Project Name:** Fortune Lab: Decoding the Jackpot  
**Purpose:** Philippine PCSO lottery analysis application with data scraping, statistical analysis, and probability-based predictions  
**Tech Stack:** Python 3.14+, Flask, Selenium, Pandas, NumPy  
**Package Manager:** `uv` (NOT pip - this is critical!)

## Core Principles

### 1. **Always Use `uv` for Package Management**
- ✅ Correct: `uv add package-name`, `uv sync`, `uv run python script.py`
- ❌ Wrong: `pip install`, `python -m pip install`
- When adding dependencies, ALWAYS use `uv add` to update `pyproject.toml`

### 2. **Maintain Modular Architecture**
The project follows a clean separation of concerns:
```
app/
├── modules/          # Core business logic
│   ├── scraper.py    # Web scraping (Selenium)
│   ├── analyzer.py   # Statistical analysis
│   └── progress_tracker.py  # Progress tracking
├── templates/        # Flask HTML templates
├── static/          # CSS, JavaScript, assets
└── data/            # JSON data storage
    ├── result_*.json         # Scraped lottery results
    ├── analysis/             # Analysis reports
    ├── progress/             # Progress tracking files
    └── accuracy/             # Accuracy validation
```

### 3. **Data Flow Understanding**
1. **Scraping:** User selects game type + date range → Selenium scrapes PCSO website → Saves to `data/result_*.json`
2. **Analysis:** Load result file → LotteryAnalyzer processes → Generate predictions → Save to `data/analysis/`
3. **Display:** Flask routes serve templates with analysis data → JavaScript renders charts

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

3. **Error Handling:** Always use try-except blocks for I/O operations
   ```python
   try:
       with open(filepath, 'r') as f:
           data = json.load(f)
   except FileNotFoundError:
       logger.error(f"File not found: {filepath}")
       raise
   except json.JSONDecodeError:
       logger.error(f"Invalid JSON: {filepath}")
       raise
   ```

4. **Logging:** Use the logging module, not print statements
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.info("Process started")
   logger.error("Error occurred", exc_info=True)
   ```

### Flask Development

1. **Route Organization:** Keep routes focused and single-purpose
   - Use `/api/*` for JSON endpoints
   - Use regular routes for page rendering

2. **Error Handling:** Implement proper error pages (404.html, 500.html)

3. **JSON Serialization:** Handle NumPy types before returning JSON
   ```python
   # Convert NumPy types to native Python
   data = convert_to_serializable(data)
   return jsonify(data)
   ```

4. **Background Tasks:** Use threading for long-running operations (scraping)
   - Return task_id immediately
   - Provide progress endpoint for polling

### Data Processing Rules

1. **NumPy/Pandas Conversions:** Always convert to native Python types before JSON serialization
   ```python
   # For integers
   value = int(numpy_value)
   
   # For floats
   value = float(numpy_value)
   
   # For arrays
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
4. **Caching:** Check if file exists before scraping (avoid duplicate work)
5. **Progress Reporting:** Use callbacks to report progress

### Analysis Guidelines

1. **Probability Disclaimer:** Always acknowledge that lottery draws are random
2. **Multiple Prediction Methods:**
   - `generate_top_predictions()` - Frequency-based
   - `generate_winning_predictions()` - Winner-optimized
   - `generate_pattern_based_prediction()` - Pattern-based
   - `generate_ultimate_predictions()` - Comprehensive

3. **Statistical Integrity:** 
   - Use appropriate statistical measures
   - Validate data before analysis
   - Handle edge cases (empty datasets, etc.)

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

### Debugging
```python
# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Flask debug mode (in app.py)
app.run(debug=True)
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
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
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

## Testing Checklist

Before committing changes, verify:

- [ ] Code runs without errors: `uv run python app.py`
- [ ] All dependencies in `pyproject.toml`
- [ ] Type hints added for new functions
- [ ] Docstrings added for new functions
- [ ] Error handling implemented
- [ ] Logging added (no print statements)
- [ ] NumPy types converted before JSON serialization
- [ ] Cross-platform compatibility considered
- [ ] UI responsive and accessible
- [ ] JavaScript errors checked in browser console

## File Modification Guidelines

### When Modifying `scraper.py`
- Test on multiple platforms if changing driver setup
- Update progress callbacks if adding steps
- Maintain backward compatibility with existing data format
- Test with different date ranges

### When Modifying `analyzer.py`
- Ensure all return values are JSON-serializable
- Test with empty datasets
- Validate statistical calculations
- Update `get_chart_data()` if adding visualizations

### When Modifying `app.py`
- Keep routes RESTful
- Add proper error handling
- Update API documentation if adding endpoints
- Test with concurrent requests

### When Modifying Templates
- Maintain consistent styling (use existing CSS classes)
- Ensure responsive design (mobile-friendly)
- Test JavaScript in multiple browsers
- Use Chart.js for visualizations (already included)

## Code Review Checklist

When reviewing code changes:

1. **Functionality:** Does it work as intended?
2. **Code Quality:** Is it clean, readable, maintainable?
3. **Error Handling:** Are edge cases handled?
4. **Performance:** Are there any bottlenecks?
5. **Security:** Are inputs validated? SQL injection safe?
6. **Documentation:** Are comments/docstrings clear?
7. **Testing:** Has it been tested adequately?
8. **Standards:** Does it follow project conventions?

## Quick Reference Commands

```bash
# Setup
uv sync

# Run application
uv run python app.py

# Add dependency
uv add package-name

# Run specific script
uv run python main.py

# Access from browser
http://localhost:5000
```

## Important URLs & Selectors

### PCSO Website
- URL: `https://www.pcso.gov.ph/SearchLottoResult.aspx`
- Selectors defined in `scraper.py:SELECTORS`

### Application Routes
- Home: `/`
- Scrape: `POST /scrape`
- Analyze: `/analyze/<filename>`
- Progress: `/api/progress/<task_id>`
- Health: `/health`

## When Things Go Wrong

### Application won't start
1. Check Python version: `python --version` (should be 3.14+)
2. Sync dependencies: `uv sync`
3. Check port 5000 is available
4. Check logs for errors

### Scraping fails
1. Check internet connection
2. Verify PCSO website is accessible
3. Check ChromeDriver is installed
4. Review Selenium error messages
5. Try with headless=False for debugging

### Analysis errors
1. Verify data file exists and is valid JSON
2. Check for empty datasets
3. Verify NumPy/Pandas versions
4. Check for missing required fields

### UI not updating
1. Clear browser cache
2. Check JavaScript console for errors
3. Verify API endpoints return correct data
4. Check network tab for failed requests

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

### Branch Naming
- `feature/description` - New features
- `fix/description` - Bug fixes
- `refactor/description` - Code refactoring
- `docs/description` - Documentation

## Performance Optimization

### Database Queries
- Currently using JSON files (appropriate for this scale)
- Consider SQLite if dataset grows beyond 100MB

### Caching
- Result files are automatically cached (don't re-scrape existing data)
- Progress files cleaned up after 5 minutes
- Analysis reports saved for historical reference

### Frontend
- Minimize JavaScript bundle size
- Use CDN for libraries (Chart.js, etc.)
- Lazy load images and charts
- Implement pagination for large result sets

## Security Considerations

1. **Input Validation:** Always validate user inputs (dates, game types)
2. **File Access:** Restrict file access to data directory only
3. **XSS Prevention:** Use Flask's auto-escaping in templates
4. **CSRF:** Add CSRF protection for forms (if implementing auth)
5. **Rate Limiting:** Consider adding rate limiting for scraping endpoints

## Future Enhancements (Ideas)

- User authentication and saved preferences
- Email notifications for new draws
- Mobile app (React Native/Flutter)
- Machine learning predictions
- Social sharing features
- Multi-language support
- Dark mode
- PDF report generation
- REST API with API keys
- WebSocket for real-time progress updates

---

**Remember:** This is an educational and entertainment application. Always include disclaimers about lottery randomness and responsible gaming.
