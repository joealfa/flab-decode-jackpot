# GitHub Copilot Instructions for Fortune Lab

## Project Context

Fortune Lab is a Philippine PCSO lottery analysis application that scrapes lottery data, performs statistical analysis, and generates probability-based predictions.

**Tech Stack:** Python 3.14+, Flask 3.1.2, Selenium 4.36.0, Pandas 2.3.3, NumPy 2.3.4  
**Package Manager:** `uv` (NOT pip - this is critical!)  
**Data Storage:** JSON files  
**Architecture:** Modular (scraper, analyzer, progress tracker)

## Critical Rules

1. **ALWAYS use `uv`** for package management
   - ✅ Correct: `uv add package-name`, `uv sync`, `uv run python script.py`
   - ❌ Wrong: `pip install`, `python -m pip install`

2. **Convert NumPy types** to native Python before JSON serialization
   ```python
   # Use convert_to_serializable() function before jsonify()
   data = convert_to_serializable(numpy_data)
   return jsonify(data)
   ```

3. **Use centralized configuration**
   ```python
   from app.config import config
   # Use config.DATA_PATH, config.HEADLESS, etc.
   ```

4. **Use custom exceptions**
   ```python
   from app.exceptions import InvalidGameTypeException, DataNotFoundException
   raise InvalidGameTypeException(game_type, valid_types)
   ```

5. **Use logging** instead of print statements
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.info("Process started")
   ```

## Code Style Standards

### Python Code
- **Type Hints:** Always use for functions
  ```python
  def analyze_data(self, data: Dict) -> Dict:
      ...
  ```

- **Docstrings:** Google-style for all modules/classes/functions
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

- **Error Handling:** Comprehensive try-except with logging
  ```python
  try:
      result = perform_operation()
  except SpecificException as e:
      logger.error(f"Operation failed: {str(e)}", exc_info=True)
      raise
  ```

### Flask Routes
- Use `/api/*` prefix for JSON endpoints
- Return consistent response format:
  ```python
  # Success
  return jsonify({'success': True, 'data': result})
  
  # Error
  return jsonify({'success': False, 'error': str(e)}), 400
  ```

## Project Structure

```
app/
├── config.py              # Centralized configuration
├── exceptions.py          # Custom exception hierarchy
├── modules/
│   ├── scraper.py         # PCSO website scraper
│   ├── analyzer.py        # Statistical analysis
│   └── progress_tracker.py # Progress management
├── templates/             # Flask HTML templates
├── static/                # CSS, JavaScript
└── data/                  # JSON data storage
```

## Supported Lottery Games

- Lotto 6/42
- Mega Lotto 6/45
- Super Lotto 6/49
- Grand Lotto 6/55
- Ultra Lotto 6/58

Format: `{game_name} {numbers_to_pick}/{max_number}`

## Common Patterns

### Adding a New Route
```python
@app.route('/api/endpoint', methods=['POST'])
def endpoint_name():
    """Description."""
    try:
        data = request.get_json()
        # Validate input
        # Process data
        result = process_data(data)
        return jsonify({'success': True, 'data': result})
    except CustomException as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400
```

### Adding Analysis Method
```python
def analyze_pattern(self) -> Dict:
    """
    Analyze specific pattern.

    Returns:
        Dictionary containing analysis results
    """
    if not self.results:
        return {}
    
    # Analysis logic
    result = {}
    
    return result
```

### File Naming Conventions
- Results: `result_{game_slug}_{end_date_YYYYMMDD}.json`
- Analysis: `analysis_{result_base_name}_{timestamp_YYYYMMDD_HHMMSS}.json`
- Use `game.replace(" ", "_").replace("/", "-")` for slugs

## Important Gotchas

⚠️ **NumPy Serialization:** Always convert before JSON
⚠️ **Progress Files:** Use atomic writes (already implemented)
⚠️ **ChromeDriver:** Multi-strategy initialization (already implemented)
⚠️ **SSL Warnings:** Python 3.14 RC2 issue, safely ignored
⚠️ **Date Formats:** PCSO uses `MM/DD/YYYY`, app uses `YYYY-MM-DD`
⚠️ **No alert():** Use `showAlert(message, type)` instead of browser `alert()` (types: `info`, `success`, `error`, `warning`)
⚠️ **No console.log:** Avoid `console.log()` in production code; use it only during active debugging and remove before committing
⚠️ **Path Traversal:** Always use `validate_filename(name, dir)` for user-supplied filenames
⚠️ **XSS Prevention:** Always use `escapeHtml()` when inserting dynamic data into `innerHTML`
⚠️ **Error Responses:** Never expose internal error details (`str(e)`) to clients

## Dependencies Management

```bash
# Add dependency
uv add package-name

# Add dev dependency
uv add --dev package-name

# Sync all dependencies
uv sync
```

## Testing

```python
# Test files in tests/ directory
# Use pytest framework
import pytest
from app.modules.analyzer import LotteryAnalyzer

def test_analyzer_initialization(sample_data):
    analyzer = LotteryAnalyzer(sample_data)
    assert analyzer.game_type == sample_data['game_type']
```

## PCSO Website Integration

- **URL:** `https://www.pcso.gov.ph/SearchLottoResult.aspx`
- **Selectors:** Defined in `scraper.py:SELECTORS` constant
- **Method:** Selenium WebDriver automation
- **Caching:** Check file existence before scraping

## Data Flow

1. **Scraping:** User input → Selenium → PCSO → JSON file
2. **Analysis:** JSON → LotteryAnalyzer → Statistics + Predictions
3. **Display:** Analysis → Flask → Templates → Charts

## Environment Variables

Load from `.env` file using python-dotenv:
```python
from dotenv import load_dotenv
load_dotenv()

from app.config import config
```

## Key Configuration

```python
from app.config import config

config.DATA_PATH          # Data directory
config.HEADLESS           # Selenium headless mode
config.LOG_LEVEL          # Logging level
config.PCSO_URL           # PCSO website URL
config.PAGE_TIMEOUT       # Selenium timeout
```

## Prediction Algorithms

1. **Top Predictions** - Frequency-based with balance
2. **Winning Predictions** - Optimized for winner patterns
3. **Pattern-Based** - Consecutive draw analysis
4. **Ultimate** - Multi-dimensional comprehensive

## API Endpoints (Key Routes)

- `POST /scrape` - Initiate scraping
- `GET /api/progress/<task_id>` - Check progress
- `GET /analyze/<filename>` - Generate analysis
- `POST /api/analyze` - API analysis (JSON)
- `GET /api/files` - List result files
- `POST /api/submit-actual-result` - Submit draw result
- `GET /api/accuracy/dashboard-data` - Accuracy dashboard data
- `GET /health` - Health check

## Frontend Patterns

### User Notifications
Use the custom modal instead of browser `alert()`:
```javascript
// Types: 'info', 'success', 'error', 'warning'
showAlert('Operation completed successfully!', 'success');
showAlert('Please enter valid numbers.', 'warning');
showAlert('Failed to load data.', 'error');
```

### XSS Prevention
Always escape dynamic data before inserting into `innerHTML`:
```javascript
// BAD - XSS vulnerable:
element.innerHTML = `<p>${serverData.message}</p>`;

// GOOD - escaped:
element.innerHTML = `<p>${escapeHtml(serverData.message)}</p>`;
```

### Path Safety (Backend)
Always validate user-supplied filenames:
```python
filepath = validate_filename(user_filename, config.DATA_PATH)
```

## References

For detailed information, refer to:
- `docs/AI_INSTRUCTIONS.md` - Complete AI guide
- `docs/ARCHITECTURE.md` - System design
- `docs/API_REFERENCE.md` - API documentation
- `docs/DEVELOPER_GUIDE.md` - Development workflow
- `docs/CODE_IMPROVEMENTS.md` - Improvement roadmap

## Best Practices Checklist

When writing code:
- [ ] Add type hints to functions
- [ ] Write Google-style docstrings
- [ ] Use logging instead of print
- [ ] Handle errors with custom exceptions
- [ ] Convert NumPy types before JSON
- [ ] Use centralized config
- [ ] Follow naming conventions
- [ ] Add appropriate error handling
- [ ] Validate inputs
- [ ] Test cross-platform compatibility

## Philosophy

- **Clean Architecture:** Separation of concerns
- **User Experience:** Elegant, intuitive interface
- **Data Integrity:** Accurate analysis and caching
- **Maintainability:** Well-documented, modular code
- **Educational Value:** Learning tool for patterns
- **Responsible Gaming:** Always acknowledge randomness

## Disclaimer

This application is for educational and entertainment purposes only. Lottery draws are random. Past performance does not guarantee future results.
