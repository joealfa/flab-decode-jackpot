# Code Improvement Recommendations

This document outlines recommended improvements to enhance code quality, maintainability, performance, and user experience.

## Completed Items

### 1. ~~Add Configuration Management~~ (COMPLETED)

**Status:** Implemented in `app/config.py`
- Centralized `Config` dataclass with environment variable support
- Auto-generated `SECRET_KEY` via `secrets.token_hex(32)`
- Secure defaults: `DEBUG=False`, `HOST=127.0.0.1`
- Sensitive value masking in `__repr__`
- Directory auto-creation on initialization
- AI/Ollama configuration support

### 2. ~~Add Environment Variable Support~~ (COMPLETED)

**Status:** Implemented with `python-dotenv` and `.env.example`
- `python-dotenv` loads `.env` before config initialization
- Comprehensive `.env.example` with all configuration options
- Includes AI/Ollama, progress cleanup, rate limiting, and feature flag settings

### 3. ~~Implement Proper Error Handling Classes~~ (COMPLETED)

**Status:** Implemented in `app/exceptions.py`
- Full exception hierarchy: `FortuneLabException` base class
- Domain-specific exceptions: Scraper, Analyzer, Data, Validation, Progress, Config, FileSystem
- HTTP-aware exceptions: `BadRequestException`, `NotFoundException`, `InternalServerException`
- `build_error_response()` utility for consistent API error formatting
- `DateRangeException` with requested/available range details

### 4. ~~Add Security Hardening~~ (COMPLETED)

**Status:** Implemented in `app.py`
- Security headers via `@app.after_request` (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, HSTS)
- Path traversal prevention with `validate_filename()`
- `escapeHtml()` JavaScript utility for XSS prevention
- `showAlert()` replaces browser `alert()`
- Generic error messages in API responses (no `str(e)` exposure)

### 5. ~~Add Comprehensive Logging~~ (COMPLETED)

**Status:** Implemented with console-only logging
- Configurable via `LOG_LEVEL` environment variable
- Third-party logger suppression (selenium, urllib3)
- Removed file-based log rotation for simplicity

### 6. ~~Add AI-Powered Analysis~~ (COMPLETED)

**Status:** Implemented in `app/modules/ai_analyzer.py`
- Ollama integration with LLaMA 3.1 8B (configurable)
- Comprehensive prompt engineering (v2) using all 8 analysis data sections
- AI status checking and model availability verification
- API endpoints: `/api/ai-analyze`, `/api/ollama-status`
- Setup guide: `docs/AI_SETUP.md`

### 7. ~~Add Accuracy Tracking~~ (COMPLETED)

**Status:** Implemented in `app/modules/accuracy_analyzer.py`
- Prediction vs actual result comparison
- Multi-algorithm accuracy scoring
- Analysis snapshot selection (pre-draw)
- Provenance tracking for audit trails
- Accuracy dashboard page
- API endpoints: `/api/accuracy-*`, `/api/verify-result`

### 8. ~~Add Background Job Scheduling~~ (COMPLETED)

**Status:** Implemented with APScheduler
- Multi-tier progress file cleanup (completed: 3min, stale: 10min, old: 24h)
- Scheduled cleanup every 5 minutes
- Graceful scheduler shutdown on app exit

### 9. ~~Add Date Range Validation~~ (COMPLETED)

**Status:** Implemented in `app/modules/scraper.py`
- Validates requested dates against PCSO website available range
- Raises `DateRangeException` with both requested and available ranges
- Prevents wasted scraping attempts for out-of-range dates

### 10. ~~Add Input Validation Layer~~ (COMPLETED)

**Status:** Implemented in `app/validators.py`
- Centralized validation functions: `require_json_body()`, `require_fields()`, `validate_game_type()`, `parse_date()`, `validate_date_range()`, `validate_lottery_numbers()`, `validate_cleanup_strategy()`
- Game type constants with max number mapping (`GAME_MAX_NUMBERS`)
- Lottery number validation: type checking, count, range, and duplicate detection
- `game_type_to_slug()` utility for consistent filename slug generation
- All routes refactored to use centralized validators
- Leverages custom exception hierarchy (`InvalidGameTypeException`, `InvalidDateRangeException`, `InvalidNumbersException`)

### 11. ~~Add Rate Limiting~~ (COMPLETED)

**Status:** Implemented with Flask-Limiter
- `Flask-Limiter` integrated with in-memory storage
- Configurable via environment variables: `RATE_LIMIT_ENABLED`, `RATE_LIMIT_SCRAPE`, `RATE_LIMIT_ANALYZE`, `RATE_LIMIT_GENERAL`
- Tier-based limits: scrape (10/hr), analyze (100/hr), general (200/hr)
- Disabled by default (`RATE_LIMIT_ENABLED=False`), enable for production
- Rate limit decorators on `/scrape`, `/api/analyze`, `/api/ai-analyze`

---

## Priority: High

### 1. Add Unit Tests

**Current Issue:** No automated testing
**Recommendation:** Implement pytest test suite

**Directory Structure:**
```
tests/
├── __init__.py
├── conftest.py
├── test_scraper.py
├── test_analyzer.py
├── test_ai_analyzer.py
├── test_accuracy_analyzer.py
├── test_progress_tracker.py
├── test_validators.py
├── test_routes.py
├── test_config.py
└── fixtures/
    ├── sample_result.json
    └── sample_analysis.json
```

**Priority Areas:**
1. `test_config.py` - Config initialization, env var loading, defaults
2. `test_validators.py` - Input validation functions, edge cases
3. `test_analyzer.py` - Statistical calculations, prediction generation
4. `test_progress_tracker.py` - Atomic writes, cleanup tiers
5. `test_routes.py` - API endpoint validation, error responses, rate limiting
6. `test_accuracy_analyzer.py` - Comparison logic, snapshot selection

---

## Priority: Medium

### 4. Add API Documentation (OpenAPI/Swagger)

**Current Issue:** No interactive API documentation
**Recommendation:** Add flask-swagger-ui or flasgger

### 5. Implement Caching with TTL

**Current Issue:** File-based caching only
**Recommendation:** Add in-memory caching for analysis results

```bash
uv add cachetools
```

### 6. Add Type Checking

**Current Issue:** No static type checking
**Recommendation:** Add mypy configuration

```bash
uv add --dev mypy types-Flask
```

### 7. Add Code Formatting & Linting

**Current Issue:** Inconsistent formatting
**Recommendation:** Add black, isort, flake8 with pre-commit hooks

```bash
uv add --dev black isort flake8 pre-commit
```

### 8. Improve Error Pages

**Current Issue:** Basic error pages (404.html, 500.html)
**Recommendation:** User-friendly error pages with navigation actions

---

## Priority: Low

### 9. Add Database Migration Support

**Current Issue:** JSON files only
**Recommendation:** Optional SQLite support for large datasets (>100MB)

### 10. Add WebSocket Support for Real-time Progress

**Current Issue:** Polling-based progress updates
**Recommendation:** WebSocket for real-time updates via Flask-SocketIO

### 11. Add Export Functionality

**Current Issue:** JSON export only
**Recommendation:** Multiple export formats (Excel, PDF, CSV)

### 12. Add Dark Mode

**Current Issue:** Light mode only
**Recommendation:** Dark mode toggle with CSS custom properties

### 13. Add User Preferences

**Current Issue:** No user customization
**Recommendation:** Local storage for preferences (theme, default game, chart type)

---

## Code Quality Improvements

### 1. Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    hooks: [trailing-whitespace, end-of-file-fixer, check-yaml]
  - repo: https://github.com/psf/black
    hooks: [black]
  - repo: https://github.com/pycqa/isort
    hooks: [isort]
  - repo: https://github.com/pycqa/flake8
    hooks: [flake8]
```

### 2. CI/CD Pipeline
- GitHub Actions for automated testing
- Linting and formatting checks
- Security scanning

### 3. Performance Optimization
- Lazy loading for charts (IntersectionObserver)
- Response compression (flask-compress)
- Faster JSON serialization (ujson)

---

**Priority Legend:**
- **High:** Critical for production readiness
- **Medium:** Important for maintainability and DX
- **Low:** Nice-to-have features for future versions

**Last Updated:** February 17, 2026
