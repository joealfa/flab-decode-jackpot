# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Complete Documentation

For comprehensive instructions and detailed documentation, refer to:

- **[AI Instructions](docs/AI_INSTRUCTIONS.md)** - Complete AI assistant guide with standards, rules, and best practices
- **[AI Setup](docs/AI_SETUP.md)** - Ollama/AI feature setup guide
- **[Architecture](docs/ARCHITECTURE.md)** - System architecture, design patterns, and component details
- **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation with examples
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Quick start and development workflow
- **[Code Improvements](docs/CODE_IMPROVEMENTS.md)** - Planned enhancements and recommendations

## Project Overview

**Name:** Fortune Lab: Decoding the Jackpot
**Purpose:** Full and deep analysis of Philippine PCSO lotto draw results with an elegant, modern dashboard displaying analysis reports, AI-powered insights, and probability-based combination predictions.

## Quick Reference

### Technology Stack

- **Language:** Python 3.14+
- **Package Manager:** `uv` (NOT pip - this is critical!)
- **Web Framework:** Flask 3.1.2
- **Web Scraping:** Selenium 4.36.0
- **Data Analysis:** Pandas 2.3.3, NumPy 2.3.4
- **AI Analysis:** Ollama 0.6.1+ (LLaMA 3.1 8B)
- **Background Jobs:** APScheduler 3.11.0
- **Environment:** python-dotenv 1.1.1
- **Data Storage:** JSON files

### Essential Commands

```bash
# Install/sync dependencies
uv sync

# Add new dependency
uv add package-name

# Run application
uv run python app.py

# Run with Flask CLI
uv run flask run

# Setup AI features (optional)
ollama serve
ollama pull llama3.1:8b
```

### Supported Lottery Games
- Lotto 6/42
- Mega Lotto 6/45
- Super Lotto 6/49
- Grand Lotto 6/55
- Ultra Lotto 6/58

### Critical Rules

1. **ALWAYS use `uv`** for package management (never pip)
2. **Convert NumPy types** to native Python before JSON serialization
3. **Follow modular architecture** - separate scraping, analysis, and presentation
4. **Use logging** instead of print statements
5. **Use custom exceptions** from `app/exceptions.py` with `build_error_response()`
6. **Use `validate_filename()`** for all user-supplied filenames
7. **Use centralized config** from `app/config.py` for all settings
8. **Cross-platform compatibility** - support Windows, Linux, macOS

### Project Structure

```
app/
├── config.py             # Centralized configuration (dataclass)
├── exceptions.py         # Custom exception hierarchy
├── modules/              # Business logic
│   ├── scraper.py        # PCSO website scraper
│   ├── analyzer.py       # Statistical analysis
│   ├── ai_analyzer.py    # AI-powered analysis (Ollama)
│   ├── accuracy_analyzer.py  # Prediction accuracy tracking
│   └── progress_tracker.py   # Progress management
├── templates/            # Flask HTML templates
├── static/               # CSS, JavaScript, assets
└── data/                 # JSON data storage
    ├── result_*.json         # Scraped results
    ├── analysis/             # Analysis reports
    ├── progress/             # Progress tracking
    └── accuracy/             # Accuracy validation
```

### Key Features Implemented

- Automated PCSO lottery data scraping with date range validation
- Advanced statistical analysis
- Multiple prediction algorithms (4 types)
- AI-powered analysis via Ollama (LLaMA 3.1)
- Day-specific pattern analysis
- Temporal trend analysis
- Interactive dashboard with Chart.js
- Progress tracking with background job scheduling (APScheduler)
- Historical report management
- Accuracy validation system with provenance tracking
- Result integrity verification
- Security headers and path traversal prevention
- Centralized configuration with `.env` support
- Custom exception hierarchy

### PCSO Website Integration

- **URL:** `https://www.pcso.gov.ph/SearchLottoResult.aspx`
- **Selectors:** Defined in `scraper.py:SELECTORS`
- **Method:** Selenium WebDriver automation
- **Caching:** Automatic to avoid duplicate scraping
- **Validation:** Date range checked against PCSO available data

### Data Flow

1. **Scraping:** User input -> Selenium -> PCSO -> JSON file
2. **Analysis:** JSON file -> LotteryAnalyzer -> Statistics + Predictions
3. **AI Analysis:** Analysis report -> AIAnalyzer -> Ollama -> AI insights
4. **Accuracy:** Actual draw -> Compare against predictions -> Accuracy report
5. **Display:** Analysis data -> Flask -> Templates -> Charts

### Code Quality Standards

- **Type Hints:** Use for all functions
- **Docstrings:** Google-style for all modules/classes/functions
- **Logging:** Use logging module with appropriate levels
- **Error Handling:** Use custom exceptions from `app/exceptions.py`
- **Testing:** Write tests for new features (pytest)
- **Formatting:** Follow PEP 8 (use black, isort)

### Common Gotchas

- **NumPy Serialization:** Always use `convert_to_serializable()` before `jsonify()`
- **Progress Files:** Use atomic writes to prevent race conditions
- **ChromeDriver:** Multi-strategy initialization for cross-platform support
- **SSL Warnings:** Python 3.14 RC2 issue, safely ignored in cleanup
- **Date Formats:** PCSO uses MM/DD/YYYY, app uses YYYY-MM-DD
- **No alert():** Use `showAlert(message, type)` instead of browser `alert()` (types: `info`, `success`, `error`, `warning`)
- **No console.log:** Remove `console.log()` calls before committing; use only during active debugging
- **Path Traversal:** Always use `validate_filename()` for user-supplied filenames before file operations
- **XSS Prevention:** Always use `escapeHtml()` when inserting server/user data into `innerHTML`
- **Error Responses:** Never expose `str(e)` to clients; log details server-side, return generic messages
- **Date Range:** Scraper validates against PCSO available range; raises `DateRangeException`
- **Secret Key:** Auto-generated with `secrets.token_hex(32)` if not set in `.env`

### When Making Changes

**Before coding:**
1. Read relevant documentation in `docs/`
2. Understand the architecture and data flow
3. Check existing implementations for patterns

**While coding:**
1. Follow established patterns and conventions
2. Add type hints and docstrings
3. Use custom exceptions with `build_error_response()`
4. Use `validate_filename()` for file operations
5. Add logging statements

**After coding:**
1. Test thoroughly with different scenarios
2. Update documentation if needed
3. Check for NumPy type conversions
4. Verify cross-platform compatibility

### Quick Task Reference

| Task | See |
|------|-----|
| Adding new route | API_REFERENCE.md, app.py examples |
| Adding analysis method | ARCHITECTURE.md, analyzer.py |
| Modifying scraper | AI_INSTRUCTIONS.md, scraper.py |
| Adding AI features | AI_SETUP.md, ai_analyzer.py |
| Adding dependency | DEVELOPER_GUIDE.md |
| Debugging issues | DEVELOPER_GUIDE.md, Common Issues |
| Improving code | CODE_IMPROVEMENTS.md |
| Understanding design | ARCHITECTURE.md |

### API Endpoints

**Web Pages:**
- `GET /` - Home page
- `GET /analyze/<filename>` - Analysis dashboard
- `GET /view-report/<filename>` - View historical report
- `GET /accuracy-dashboard` - Accuracy dashboard
- `GET /health` - Health check

**Core API:**
- `POST /scrape` - Initiate scraping
- `GET /api/progress/<task_id>` - Check progress
- `POST /api/analyze` - API analysis
- `GET /api/files` - List result files
- `GET /api/result-files` - Result files by game type
- `GET /api/analysis-history/<filename>` - Analysis history

**AI API:**
- `POST /api/ai-analyze` - AI-powered analysis
- `GET /api/ollama-status` - Ollama service status

**Accuracy API:**
- `POST /api/submit-actual-result` - Submit draw result
- `GET /api/accuracy-analysis` - Accuracy analysis
- `GET /api/accuracy-summary` - Accuracy summary
- `GET /api/accuracy-provenance` - Accuracy provenance
- `GET /api/verify-result` - Verify result integrity
- `GET /api/accuracy-files` - List accuracy files

**Management API:**
- `DELETE /api/delete-report/<filename>` - Delete report
- `GET /api/export-analysis/<filename>` - Export report
- `POST /api/cleanup-progress` - Cleanup progress files

See `docs/API_REFERENCE.md` for complete API documentation.

## Philosophy

This project emphasizes:
- **Clean Architecture:** Separation of concerns
- **User Experience:** Elegant, intuitive interface
- **Data Integrity:** Accurate analysis and caching
- **Security:** Headers, input validation, path traversal prevention
- **Maintainability:** Well-documented, modular code
- **Educational Value:** Learning tool for lottery patterns
- **Responsible Gaming:** Always acknowledge randomness

## Disclaimer

This application is for **educational and entertainment purposes only**. Lottery draws are random events. Past performance does not guarantee future results. Please gamble responsibly.

---

**For detailed information, always refer to the comprehensive documentation in the `docs/` folder.**
