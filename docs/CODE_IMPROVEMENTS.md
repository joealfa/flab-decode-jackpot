# Code Improvement Recommendations

This document outlines recommended improvements to enhance code quality, maintainability, performance, and user experience.

## Priority: High

### 1. Add Configuration Management

**Current Issue:** Configuration scattered across modules  
**Recommendation:** Create centralized configuration

**Implementation:**
```python
# app/config.py
import os
from dataclasses import dataclass

@dataclass
class Config:
    """Application configuration."""
    # Flask
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'fortune-lab-secret-key-2024')
    DEBUG: bool = os.environ.get('DEBUG', 'False').lower() == 'true'
    HOST: str = os.environ.get('HOST', '0.0.0.0')
    PORT: int = int(os.environ.get('PORT', 5000))
    
    # Data paths
    DATA_PATH: str = 'app/data'
    ANALYSIS_PATH: str = 'app/data/analysis'
    PROGRESS_PATH: str = 'app/data/progress'
    ACCURACY_PATH: str = 'app/data/accuracy'
    
    # Scraper
    HEADLESS: bool = os.environ.get('HEADLESS', 'True').lower() == 'true'
    PCSO_URL: str = 'https://www.pcso.gov.ph/SearchLottoResult.aspx'
    PAGE_TIMEOUT: int = 30
    
    # Progress tracking
    PROGRESS_CLEANUP_AGE: int = 300  # 5 minutes
    
    # Logging
    LOG_LEVEL: str = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.environ.get('LOG_FILE', 'app.log')

config = Config()
```

**Usage:**
```python
from app.config import config

app.config['SECRET_KEY'] = config.SECRET_KEY
scraper = PCSOScraper(headless=config.HEADLESS)
```

### 2. Add Environment Variable Support

**Current Issue:** No `.env` file support  
**Recommendation:** Add python-dotenv

**Implementation:**
```bash
uv add python-dotenv
```

Create `.env`:
```env
DEBUG=True
SECRET_KEY=your-secret-key-here
HEADLESS=False
LOG_LEVEL=DEBUG
```

Update `app.py`:
```python
from dotenv import load_dotenv
load_dotenv()

from app.config import config
```

Create `.env.example`:
```env
# Flask Configuration
DEBUG=False
SECRET_KEY=change-me-in-production
HOST=0.0.0.0
PORT=5000

# Scraper Configuration
HEADLESS=True
PAGE_TIMEOUT=30

# Logging
LOG_LEVEL=INFO
LOG_FILE=app.log
```

### 3. Implement Proper Error Handling Classes

**Current Issue:** Generic exceptions  
**Recommendation:** Custom exception hierarchy

**Implementation:**
```python
# app/exceptions.py
class FortuneLabException(Exception):
    """Base exception for Fortune Lab."""
    pass

class ScraperException(FortuneLabException):
    """Scraper-related errors."""
    pass

class AnalyzerException(FortuneLabException):
    """Analyzer-related errors."""
    pass

class DataNotFoundException(FortuneLabException):
    """Data file not found."""
    pass

class InvalidGameTypeException(FortuneLabException):
    """Invalid game type specified."""
    pass

class DateRangeException(FortuneLabException):
    """Invalid date range."""
    pass
```

**Usage:**
```python
from app.exceptions import InvalidGameTypeException

if game_type not in self.GAME_TYPES:
    raise InvalidGameTypeException(
        f"Invalid game type: {game_type}. "
        f"Must be one of: {list(self.GAME_TYPES.keys())}"
    )
```

### 4. Add Input Validation Layer

**Current Issue:** Validation scattered across routes  
**Recommendation:** Centralized validation with Pydantic

**Implementation:**
```bash
uv add pydantic pydantic-settings
```

```python
# app/validators.py
from pydantic import BaseModel, validator, Field
from datetime import datetime, date
from typing import List, Optional

class ScrapeRequest(BaseModel):
    game_type: str
    start_date: date
    end_date: date
    
    @validator('game_type')
    def validate_game_type(cls, v):
        valid_games = [
            'Lotto 6/42', 'Mega Lotto 6/45', 'Super Lotto 6/49',
            'Grand Lotto 6/55', 'Ultra Lotto 6/58'
        ]
        if v not in valid_games:
            raise ValueError(f'Invalid game type. Must be one of: {valid_games}')
        return v
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v

class ActualResultRequest(BaseModel):
    game_type: str
    draw_date: date
    numbers: List[int] = Field(min_items=6, max_items=6)
    jackpot: Optional[str] = "N/A"
    winners: Optional[str] = "N/A"
    
    @validator('numbers')
    def validate_numbers(cls, v):
        if len(v) != 6:
            raise ValueError('Must provide exactly 6 numbers')
        if len(set(v)) != 6:
            raise ValueError('All numbers must be unique')
        if any(n < 1 for n in v):
            raise ValueError('All numbers must be positive')
        return sorted(v)
```

**Usage in routes:**
```python
from app.validators import ScrapeRequest
from pydantic import ValidationError

@app.route('/scrape', methods=['POST'])
def scrape_data():
    try:
        request_data = ScrapeRequest(**request.get_json())
        # Process with validated data
        game_type = request_data.game_type
        start_date = datetime.combine(request_data.start_date, datetime.min.time())
        end_date = datetime.combine(request_data.end_date, datetime.min.time())
        
    except ValidationError as e:
        return jsonify({'success': False, 'errors': e.errors()}), 400
```

### 5. Add Comprehensive Logging

**Current Issue:** Inconsistent logging  
**Recommendation:** Structured logging with rotation

**Implementation:**
```python
# app/logging_config.py
import logging
import logging.handlers
import os
from app.config import config

def setup_logging():
    """Configure application logging."""
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        f'logs/{config.LOG_FILE}',
        maxBytes=10_000_000,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    return logger
```

**Usage in `app.py`:**
```python
from app.logging_config import setup_logging

logger = setup_logging()
logger.info("Application started")
```

## Priority: Medium

### 6. Add Unit Tests

**Current Issue:** No automated testing  
**Recommendation:** Implement pytest test suite

**Implementation:**
```bash
uv add pytest pytest-cov pytest-mock
```

**Directory Structure:**
```
tests/
├── __init__.py
├── conftest.py
├── test_scraper.py
├── test_analyzer.py
├── test_progress_tracker.py
├── test_routes.py
└── fixtures/
    ├── sample_result.json
    └── sample_analysis.json
```

**Example Test:**
```python
# tests/test_analyzer.py
import pytest
import json
from app.modules.analyzer import LotteryAnalyzer

@pytest.fixture
def sample_data():
    """Load sample lottery data."""
    with open('tests/fixtures/sample_result.json', 'r') as f:
        return json.load(f)

def test_analyzer_initialization(sample_data):
    """Test analyzer initializes correctly."""
    analyzer = LotteryAnalyzer(sample_data)
    assert analyzer.game_type == sample_data['game_type']
    assert len(analyzer.results) == sample_data['total_draws']

def test_overall_statistics(sample_data):
    """Test overall statistics calculation."""
    analyzer = LotteryAnalyzer(sample_data)
    stats = analyzer.get_overall_statistics()
    
    assert 'total_draws' in stats
    assert 'most_frequent_numbers' in stats
    assert stats['total_draws'] == sample_data['total_draws']

def test_prediction_generation(sample_data):
    """Test prediction generation."""
    analyzer = LotteryAnalyzer(sample_data)
    predictions = analyzer.generate_top_predictions(top_n=5)
    
    assert len(predictions) == 5
    assert all('numbers' in p for p in predictions)
    assert all('confidence_score' in p for p in predictions)
    assert all(len(p['numbers']) == 6 for p in predictions)
```

### 7. Add API Documentation

**Current Issue:** No API documentation  
**Recommendation:** Add OpenAPI/Swagger documentation

**Implementation:**
```bash
uv add flask-swagger-ui
```

```python
# app/swagger.py
from flask_swagger_ui import get_swaggerui_blueprint

SWAGGER_URL = '/api/docs'
API_URL = '/static/swagger.json'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Fortune Lab API"
    }
)
```

Create `app/static/swagger.json`:
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Fortune Lab API",
    "version": "1.0.0",
    "description": "PCSO Lottery Analysis API"
  },
  "paths": {
    "/api/files": {
      "get": {
        "summary": "List all result files",
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "success": {"type": "boolean"},
                    "files": {
                      "type": "array",
                      "items": {"$ref": "#/components/schemas/ResultFile"}
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "ResultFile": {
        "type": "object",
        "properties": {
          "filename": {"type": "string"},
          "game_type": {"type": "string"},
          "total_draws": {"type": "integer"},
          "date_range": {"type": "string"},
          "scraped_at": {"type": "string"}
        }
      }
    }
  }
}
```

### 8. Implement Caching with TTL

**Current Issue:** File-based caching only  
**Recommendation:** Add in-memory caching for analysis results

**Implementation:**
```bash
uv add cachetools
```

```python
# app/cache.py
from cachetools import TTLCache
import hashlib
import json

# Analysis cache (100 items, 1 hour TTL)
analysis_cache = TTLCache(maxsize=100, ttl=3600)

def get_cache_key(data: dict) -> str:
    """Generate cache key from data."""
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.md5(json_str.encode()).hexdigest()

def get_cached_analysis(cache_key: str):
    """Get analysis from cache."""
    return analysis_cache.get(cache_key)

def set_cached_analysis(cache_key: str, data: dict):
    """Store analysis in cache."""
    analysis_cache[cache_key] = data
```

**Usage:**
```python
from app.cache import get_cached_analysis, set_cached_analysis, get_cache_key

@app.route('/analyze/<filename>')
def analyze(filename):
    cache_key = get_cache_key({'filename': filename, 'type': 'analysis'})
    
    # Check cache first
    cached = get_cached_analysis(cache_key)
    if cached:
        return render_template('dashboard.html', **cached)
    
    # Perform analysis...
    analysis_data = perform_analysis(filename)
    
    # Store in cache
    set_cached_analysis(cache_key, analysis_data)
    
    return render_template('dashboard.html', **analysis_data)
```

### 9. Add Rate Limiting

**Current Issue:** No protection against abuse  
**Recommendation:** Implement rate limiting

**Implementation:**
```bash
uv add Flask-Limiter
```

```python
# app/__init__.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Apply to routes
@app.route('/scrape', methods=['POST'])
@limiter.limit("10 per hour")  # Limit scraping requests
def scrape_data():
    ...

@app.route('/api/analyze', methods=['POST'])
@limiter.limit("100 per hour")
def api_analyze():
    ...
```

### 10. Improve Error Pages

**Current Issue:** Basic error pages  
**Recommendation:** User-friendly error pages with actions

**Implementation:**
```html
<!-- app/templates/error.html -->
{% extends "base.html" %}

{% block content %}
<div class="error-container">
    <div class="error-icon">
        {% if error_code == 404 %}
        <i class="fas fa-search fa-5x"></i>
        {% elif error_code == 500 %}
        <i class="fas fa-exclamation-triangle fa-5x"></i>
        {% else %}
        <i class="fas fa-times-circle fa-5x"></i>
        {% endif %}
    </div>
    
    <h1>{{ error_code }}</h1>
    <h2>{{ error_title }}</h2>
    <p>{{ error_message }}</p>
    
    <div class="error-actions">
        <a href="/" class="btn btn-primary">Go Home</a>
        <a href="javascript:history.back()" class="btn btn-secondary">Go Back</a>
        {% if show_support %}
        <a href="/support" class="btn btn-outline">Contact Support</a>
        {% endif %}
    </div>
    
    {% if debug_info and app.debug %}
    <div class="debug-info">
        <h3>Debug Information</h3>
        <pre>{{ debug_info }}</pre>
    </div>
    {% endif %}
</div>
{% endblock %}
```

## Priority: Low

### 11. Add Database Migration Support

**Current Issue:** JSON files only  
**Recommendation:** Optional SQLite support for large datasets

**Implementation:**
```bash
uv add sqlalchemy alembic
```

```python
# app/models.py
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class LotteryDraw(Base):
    __tablename__ = 'lottery_draws'
    
    id = Column(Integer, primary_key=True)
    game_type = Column(String(50), nullable=False, index=True)
    draw_date = Column(DateTime, nullable=False, index=True)
    day_of_week = Column(String(20))
    numbers = Column(JSON)  # Store as JSON array
    jackpot = Column(String(50))
    winners = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)

class AnalysisReport(Base):
    __tablename__ = 'analysis_reports'
    
    id = Column(Integer, primary_key=True)
    source_file = Column(String(255))
    game_type = Column(String(50), index=True)
    analyzed_at = Column(DateTime, default=datetime.now)
    report_data = Column(JSON)  # Full analysis as JSON
```

### 12. Add WebSocket Support for Real-time Progress

**Current Issue:** Polling-based progress updates  
**Recommendation:** WebSocket for real-time updates

**Implementation:**
```bash
uv add flask-socketio python-socketio
```

```python
# app/__init__.py
from flask_socketio import SocketIO, emit

socketio = SocketIO(app, cors_allowed_origins="*")

# Progress tracker update
def update_progress_websocket(task_id, progress_data):
    socketio.emit('progress_update', {
        'task_id': task_id,
        'data': progress_data
    }, room=task_id)

# Client joins room
@socketio.on('join_progress')
def join_progress(data):
    task_id = data['task_id']
    join_room(task_id)
    emit('joined', {'task_id': task_id})
```

### 13. Add Export Functionality

**Current Issue:** Limited export options  
**Recommendation:** Multiple export formats

**Implementation:**
```bash
uv add openpyxl reportlab
```

```python
# app/exporters.py
import openpyxl
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import csv

class ExportManager:
    @staticmethod
    def export_to_excel(data, filename):
        """Export analysis to Excel."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Analysis Report"
        
        # Add headers
        ws.append(['Metric', 'Value'])
        
        # Add data
        for key, value in data.items():
            ws.append([key, str(value)])
        
        wb.save(filename)
    
    @staticmethod
    def export_to_pdf(data, filename):
        """Export analysis to PDF."""
        c = canvas.Canvas(filename, pagesize=letter)
        c.drawString(100, 750, "Fortune Lab Analysis Report")
        
        y = 700
        for key, value in data.items():
            c.drawString(100, y, f"{key}: {value}")
            y -= 20
        
        c.save()
    
    @staticmethod
    def export_to_csv(data, filename):
        """Export predictions to CSV."""
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Rank', 'Numbers', 'Score'])
            
            for idx, pred in enumerate(data, 1):
                writer.writerow([
                    idx,
                    ','.join(map(str, pred['numbers'])),
                    pred.get('confidence_score', 0)
                ])
```

### 14. Add User Preferences

**Current Issue:** No user customization  
**Recommendation:** Local storage for preferences

**Implementation:**
```javascript
// app/static/js/preferences.js
class Preferences {
    constructor() {
        this.defaults = {
            theme: 'light',
            defaultGameType: 'Lotto 6/42',
            chartType: 'bar',
            autoRefresh: true,
            notificationsEnabled: false
        };
    }
    
    get(key) {
        const stored = localStorage.getItem(`flab_${key}`);
        return stored !== null ? JSON.parse(stored) : this.defaults[key];
    }
    
    set(key, value) {
        localStorage.setItem(`flab_${key}`, JSON.stringify(value));
        this.applyPreference(key, value);
    }
    
    applyPreference(key, value) {
        switch(key) {
            case 'theme':
                document.body.className = `theme-${value}`;
                break;
            case 'autoRefresh':
                this.toggleAutoRefresh(value);
                break;
        }
    }
}

const prefs = new Preferences();
```

### 15. Add Dark Mode

**Current Issue:** Light mode only  
**Recommendation:** Dark mode toggle

**Implementation:**
```css
/* app/static/css/dark-mode.css */
[data-theme="dark"] {
    --primary-color: #818cf8;
    --primary-dark: #6366f1;
    --secondary-color: #34d399;
    --bg-color: #0f172a;
    --white: #1e293b;
    --dark: #f1f5f9;
    --dark-light: #cbd5e1;
    --light-gray: #334155;
}

[data-theme="dark"] body {
    background: var(--bg-color);
    color: var(--dark);
}

[data-theme="dark"] .card {
    background: var(--white);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}
```

```javascript
// Dark mode toggle
function toggleDarkMode() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

// Load saved theme
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
});
```

## Code Quality Improvements

### 1. Add Type Checking

```bash
uv add mypy types-Flask
```

Create `mypy.ini`:
```ini
[mypy]
python_version = 3.14
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_any_unimported = True

[mypy-selenium.*]
ignore_missing_imports = True

[mypy-pandas.*]
ignore_missing_imports = True
```

### 2. Add Code Formatting

```bash
uv add black isort
```

Create `pyproject.toml` section:
```toml
[tool.black]
line-length = 88
target-version = ['py314']
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 88
```

### 3. Add Linting

```bash
uv add flake8 pylint
```

Create `.flake8`:
```ini
[flake8]
max-line-length = 88
extend-ignore = E203, E501
exclude = .git,__pycache__,venv
```

### 4. Add Pre-commit Hooks

```bash
uv add pre-commit
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

## Performance Improvements

### 1. Database Indexing (if using SQLite)
```python
# Add indexes for frequently queried fields
Index('idx_game_type_date', LotteryDraw.game_type, LotteryDraw.draw_date)
Index('idx_draw_date', LotteryDraw.draw_date)
```

### 2. Lazy Loading for Charts
```javascript
// Load charts only when visible
const chartObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            loadChart(entry.target);
            chartObserver.unobserve(entry.target);
        }
    });
});

document.querySelectorAll('.chart-container').forEach(chart => {
    chartObserver.observe(chart);
});
```

### 3. Optimize JSON Serialization
```python
# Use ujson for faster JSON operations
uv add ujson

import ujson as json  # Drop-in replacement
```

### 4. Add Compression
```python
from flask_compress import Compress

compress = Compress()
compress.init_app(app)
```

---

**Priority Legend:**
- **High:** Critical for production deployment
- **Medium:** Important for maintainability and UX
- **Low:** Nice-to-have features for future versions

**Implementation Timeline:**
1. Week 1: High priority items (1-5)
2. Week 2: Medium priority items (6-10)
3. Week 3: Low priority items (11-15)
4. Week 4: Code quality and performance improvements
