# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 📚 Complete Documentation

For comprehensive instructions and detailed documentation, refer to:

- **[AI Instructions](docs/AI_INSTRUCTIONS.md)** - Complete AI assistant guide with standards, rules, and best practices
- **[Architecture](docs/ARCHITECTURE.md)** - System architecture, design patterns, and component details
- **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation with examples
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Quick start and development workflow
- **[Code Improvements](docs/CODE_IMPROVEMENTS.md)** - Planned enhancements and recommendations

## Project Overview

**Name:** Fortune Lab: Decoding the Jackpot  
**Purpose:** Full and deep analysis of Philippine PCSO lotto draw results with an elegant, modern dashboard displaying analysis reports and probability-based combination predictions.

## Quick Reference

### Technology Stack

- **Language:** Python 3.14+
- **Package Manager:** `uv` (NOT pip - this is critical!)
- **Web Framework:** Flask 3.1.2
- **Web Scraping:** Selenium 4.36.0
- **Data Analysis:** Pandas 2.3.3, NumPy 2.3.4
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
5. **Handle errors gracefully** with try-except blocks
6. **Cross-platform compatibility** - support Windows, Linux, macOS

### Project Structure

```
app/
├── modules/          # Business logic
│   ├── scraper.py    # PCSO website scraper
│   ├── analyzer.py   # Statistical analysis
│   └── progress_tracker.py  # Progress management
├── templates/        # Flask HTML templates
├── static/          # CSS, JavaScript, assets
└── data/            # JSON data storage
    ├── result_*.json         # Scraped results
    ├── analysis/             # Analysis reports
    ├── progress/             # Progress tracking
    └── accuracy/             # Accuracy validation
```

### Key Features Implemented

✅ Automated PCSO lottery data scraping  
✅ Advanced statistical analysis  
✅ Multiple prediction algorithms (4 types)  
✅ Day-specific pattern analysis  
✅ Temporal trend analysis  
✅ Interactive dashboard with Chart.js  
✅ Progress tracking for async operations  
✅ Historical report management  
✅ Accuracy validation system  

### PCSO Website Integration

- **URL:** `https://www.pcso.gov.ph/SearchLottoResult.aspx`
- **Selectors:** Defined in `scraper.py:SELECTORS`
- **Method:** Selenium WebDriver automation
- **Caching:** Automatic to avoid duplicate scraping

### Data Flow

1. **Scraping:** User input → Selenium → PCSO → JSON file
2. **Analysis:** JSON file → LotteryAnalyzer → Statistics + Predictions
3. **Display:** Analysis data → Flask → Templates → Charts

### Code Quality Standards

- **Type Hints:** Use for all functions
- **Docstrings:** Google-style for all modules/classes/functions
- **Logging:** Use logging module with appropriate levels
- **Error Handling:** Comprehensive try-except blocks
- **Testing:** Write tests for new features (pytest)
- **Formatting:** Follow PEP 8 (use black, isort)

### Common Gotchas

⚠️ **NumPy Serialization:** Always use `convert_to_serializable()` before `jsonify()`  
⚠️ **Progress Files:** Use atomic writes to prevent race conditions  
⚠️ **ChromeDriver:** Multi-strategy initialization for cross-platform support  
⚠️ **SSL Warnings:** Python 3.14 RC2 issue, safely ignored in cleanup  
⚠️ **Date Formats:** PCSO uses MM/DD/YYYY, app uses YYYY-MM-DD  

### When Making Changes

**Before coding:**
1. Read relevant documentation in `docs/`
2. Understand the architecture and data flow
3. Check existing implementations for patterns

**While coding:**
1. Follow established patterns and conventions
2. Add type hints and docstrings
3. Implement proper error handling
4. Add logging statements

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
| Adding dependency | DEVELOPER_GUIDE.md |
| Debugging issues | DEVELOPER_GUIDE.md, Common Issues |
| Improving code | CODE_IMPROVEMENTS.md |
| Understanding design | ARCHITECTURE.md |

### API Endpoints

- `POST /scrape` - Initiate scraping
- `GET /api/progress/<task_id>` - Check progress
- `GET /analyze/<filename>` - Generate analysis
- `POST /api/analyze` - API analysis
- `GET /api/files` - List result files
- `POST /api/submit-actual-result` - Submit draw result
- `GET /health` - Health check

See `docs/API_REFERENCE.md` for complete API documentation.

## Philosophy

This project emphasizes:
- **Clean Architecture:** Separation of concerns
- **User Experience:** Elegant, intuitive interface
- **Data Integrity:** Accurate analysis and caching
- **Maintainability:** Well-documented, modular code
- **Educational Value:** Learning tool for lottery patterns
- **Responsible Gaming:** Always acknowledge randomness

## Disclaimer

This application is for **educational and entertainment purposes only**. Lottery draws are random events. Past performance does not guarantee future results. Please gamble responsibly.

---

**For detailed information, always refer to the comprehensive documentation in the `docs/` folder.**
