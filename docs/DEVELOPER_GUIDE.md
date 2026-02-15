# Developer Quick Start Guide

Get started with Fortune Lab development in minutes.

## Prerequisites

- **Python 3.14+** - [Download](https://www.python.org/downloads/)
- **uv** - Python package manager
  ```bash
  # Windows (PowerShell)
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  
  # macOS/Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- **Chrome Browser** - For Selenium WebDriver
- **Git** - For version control

## Initial Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd flab-decode-jackpot
```

### 2. Install Dependencies
```bash
# Sync all dependencies from pyproject.toml
uv sync
```

This will create a virtual environment and install:
- Flask 3.1.2
- Selenium 4.36.0
- Pandas 2.3.3
- NumPy 2.3.4
- webdriver-manager 4.0.2
- APScheduler 3.11.0
- python-dotenv 1.1.1
- ollama 0.6.1+

### 3. Verify Installation
```bash
# Check Python version
uv run python --version
# Should show Python 3.14+

# Test import
uv run python -c "import flask; import selenium; import pandas; print('All imports successful!')"
```

## Running the Application

### Development Server

```bash
# Method 1: Direct execution
uv run python app.py

# Method 2: Flask CLI
uv run flask run
```

The application will be available at:
- Local: http://localhost:5000 (default, bind to 127.0.0.1)
- Network: Set `HOST=0.0.0.0` in `.env` to allow external access

### Production Server (Future)

```bash
# Install Gunicorn
uv add gunicorn

# Run with Gunicorn
uv run gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Project Structure Quick Reference

```
flab-decode-jackpot/
├── app.py                    # Main Flask application
├── pyproject.toml            # Dependencies and project config
├── README.md                 # Project overview
├── CLAUDE.md                 # AI assistant guidance
│
├── app/                      # Application package
│   ├── __init__.py
│   ├── config.py             # Centralized configuration (dataclass)
│   ├── exceptions.py         # Custom exception hierarchy
│   ├── modules/              # Business logic
│   │   ├── __init__.py
│   │   ├── scraper.py        # PCSO website scraper
│   │   ├── analyzer.py       # Statistical analysis
│   │   ├── ai_analyzer.py    # AI-powered analysis (Ollama)
│   │   ├── accuracy_analyzer.py  # Prediction accuracy tracking
│   │   └── progress_tracker.py   # Progress management
│   │
│   ├── templates/            # HTML templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── dashboard.html
│   │   ├── accuracy_dashboard.html
│   │   ├── test_chart.html
│   │   ├── 404.html
│   │   └── 500.html
│   │
│   ├── static/               # Static assets
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── main.js
│   │
│   └── data/                 # Data storage
│       ├── result_*.json     # Scraped results
│       ├── analysis/         # Analysis reports
│       ├── progress/         # Progress tracking
│       └── accuracy/         # Accuracy validation
│
└── docs/                     # Documentation
    ├── AI_INSTRUCTIONS.md    # AI assistant instructions
    ├── AI_SETUP.md           # Ollama/AI setup guide
    ├── ARCHITECTURE.md       # System architecture
    ├── API_REFERENCE.md      # API documentation
    ├── CODE_IMPROVEMENTS.md  # Improvement recommendations
    └── DEVELOPER_GUIDE.md    # This file
```

## Common Development Tasks

### Adding a New Dependency

```bash
# Add package
uv add package-name

# Add dev dependency
uv add --dev package-name

# Sync after manual pyproject.toml edit
uv sync
```

### Running Tests (After Setup)

```bash
# Install pytest
uv add --dev pytest pytest-cov

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=app tests/
```

### Code Formatting

```bash
# Install formatters
uv add --dev black isort flake8

# Format code
uv run black .
uv run isort .

# Check linting
uv run flake8 app/
```

### Database Migrations (Future)

```bash
# Install Alembic
uv add alembic

# Initialize
uv run alembic init migrations

# Create migration
uv run alembic revision --autogenerate -m "Description"

# Apply migration
uv run alembic upgrade head
```

## Development Workflow

### 1. Feature Development

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes...

# Test changes
uv run python app.py

# Format and lint
uv run black .
uv run flake8 app/

# Commit
git add .
git commit -m "feat: add your feature"

# Push
git push origin feature/your-feature-name
```

### 2. Adding a New Route

```python
# In app.py

@app.route('/your-route', methods=['GET', 'POST'])
def your_route():
    """
    Your route description.
    """
    try:
        # Your logic here
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"Error in your_route: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
```

### 3. Adding a New Analysis Method

```python
# In app/modules/analyzer.py

def your_analysis_method(self) -> Dict:
    """
    Your analysis description.

    Returns:
        Dictionary containing analysis results
    """
    if not self.results:
        return {}

    # Your analysis logic
    result = {}

    return result
```

Then update `app.py` to include it:

```python
# In analyze() route
your_analysis = analyzer.your_analysis_method()

return render_template(
    'dashboard.html',
    your_analysis=your_analysis,
    # ... other data
)
```

### 4. Adding a New Template

```html
<!-- app/templates/your_template.html -->
{% extends "base.html" %}

{% block title %}Your Page Title{% endblock %}

{% block content %}
<div class="container">
    <h1>Your Page</h1>
    <!-- Your content -->
</div>
{% endblock %}

{% block scripts %}
<script>
    // Your JavaScript
</script>
{% endblock %}
```

## Debugging

### Enable Debug Mode

Set in your `.env` file:
```env
DEBUG=True
LOG_LEVEL=DEBUG
```

### Setting Up AI Features (Optional)

See [AI Setup Guide](AI_SETUP.md) for detailed instructions.

```bash
# Quick start
ollama serve          # Start Ollama service
ollama pull llama3.1:8b  # Download the model
```

Configure in `.env`:
```env
OLLAMA_ENABLED=True
OLLAMA_MODEL=llama3.1:8b
OLLAMA_HOST=http://localhost:11434
OLLAMA_TIMEOUT=120
```

### Flask Debug Toolbar (Optional)

```bash
uv add flask-debugtoolbar
```

```python
# In app.py
from flask_debugtoolbar import DebugToolbarExtension

app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
toolbar = DebugToolbarExtension(app)
```

### VS Code Debugging

Create `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Flask",
            "type": "debugpy",
            "request": "launch",
            "module": "flask",
            "env": {
                "FLASK_APP": "app.py",
                "FLASK_DEBUG": "1"
            },
            "args": [
                "run",
                "--no-debugger",
                "--no-reload"
            ],
            "jinja": true,
            "justMyCode": true
        }
    ]
}
```

## Testing

### Manual Testing Workflow

1. **Start Application**
   ```bash
   uv run python app.py
   ```

2. **Open Browser**
   - Navigate to http://localhost:5000

3. **Test Scraping**
   - Select game type
   - Choose date range
   - Click "Generate Analysis"
   - Monitor progress

4. **Test Analysis**
   - Click on result file
   - Verify analysis displays correctly
   - Check all charts render
   - Test predictions

### API Testing with cURL

```bash
# Test scraping
curl -X POST http://localhost:5000/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "game_type": "Lotto 6/42",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  }'

# Get progress (replace task_id)
curl http://localhost:5000/api/progress/your-task-id

# List files
curl http://localhost:5000/api/files

# Health check
curl http://localhost:5000/health
```

### API Testing with Postman

1. Use a tool like Postman or cURL to test API endpoints
2. Set base URL: `http://localhost:5000`
3. See `docs/API_REFERENCE.md` for complete endpoint documentation

## Common Issues and Solutions

### Issue: `uv: command not found`

**Solution:**
```bash
# Reinstall uv
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Add to PATH (Windows)
# Add C:\Users\<username>\.cargo\bin to PATH environment variable
```

### Issue: ChromeDriver not found

**Solution:**
```bash
# The app uses webdriver-manager, it should auto-download
# If issues persist, manually install:

# Windows (via Chocolatey)
choco install chromedriver

# macOS
brew install chromedriver

# Linux
sudo apt-get install chromium-chromedriver
```

### Issue: Port 5000 already in use

**Solution:**
```bash
# Change port in app.py:
app.run(debug=True, port=5001)

# Or kill process on port 5000 (Windows)
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Issue: SSL errors with Python 3.14 RC2

**Solution:**
This is a known issue with Python 3.14 RC2. The code already handles it gracefully in the `finally` block of the scraper. Safe to ignore.

### Issue: NumPy JSON serialization errors

**Solution:**
Use the `convert_to_serializable()` function before returning JSON:

```python
from app.py import convert_to_serializable

data = convert_to_serializable(numpy_data)
return jsonify(data)
```

## Environment Setup

### Recommended VS Code Extensions

- Python (Microsoft)
- Pylance
- Python Debugger
- Flask Snippets
- GitLens
- Better Comments
- Auto Rename Tag
- ESLint (for JavaScript)

### Recommended Settings

Create `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.testing.pytestEnabled": true,
    "editor.formatOnSave": true,
    "editor.rulers": [88],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```

## Git Workflow

### Initial Setup

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### .gitignore

Ensure `.gitignore` includes:

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
ENV/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Application
app/data/
logs/
*.log

# Environment
.env
.env.local
```

### Commit Message Convention

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (formatting)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance

Examples:
```
feat(analyzer): add monthly trend analysis

Implemented comprehensive monthly pattern analysis
including hot numbers per month and seasonal trends.

Closes #123
```

## Documentation

### Key Documentation Files

1. **AI_INSTRUCTIONS.md** - Instructions for AI assistants
2. **AI_SETUP.md** - Ollama/AI feature setup guide
3. **ARCHITECTURE.md** - System architecture and design
4. **API_REFERENCE.md** - Complete API documentation
5. **CODE_IMPROVEMENTS.md** - Planned improvements
6. **DEVELOPER_GUIDE.md** - This file

### Updating Documentation

- Update docs when adding features
- Keep API reference in sync with routes
- Document breaking changes
- Add examples for complex features

## Performance Tips

### 1. Use Caching
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_function(param):
    # Expensive computation
    return result
```

### 2. Profile Code
```bash
uv add --dev py-spy

# Profile running application
py-spy top -- python app.py
```

### 3. Optimize Database Queries (Future)
```python
# Use indexes
# Batch operations
# Limit query results
```

### 4. Minimize DOM Operations
```javascript
// Bad
for (let i = 0; i < 1000; i++) {
    element.innerHTML += `<div>${i}</div>`;
}

// Good
let html = '';
for (let i = 0; i < 1000; i++) {
    html += `<div>${i}</div>`;
}
element.innerHTML = html;
```

## Deployment

### Production Checklist

- [ ] Set `DEBUG=False` (default)
- [ ] Set `SECRET_KEY` in `.env` (auto-generated if not set)
- [ ] Set `HOST=127.0.0.1` or behind reverse proxy (default)
- [ ] Enable HTTPS via reverse proxy
- [ ] Configure CORS if needed
- [ ] Add rate limiting
- [ ] Set up monitoring (`/health` endpoint)
- [ ] Configure backups for `app/data/` directory
- [ ] Add authentication
- [ ] Set up Ollama for AI features (optional)
- [ ] Update documentation

### Deployment Options

1. **DigitalOcean App Platform**
2. **AWS Elastic Beanstalk**
3. **Heroku**
4. **Railway**
5. **Render**
6. **Self-hosted (VPS)**

Refer to the hosting platform's documentation for deployment-specific instructions.

## Getting Help

### Internal Resources
- Read documentation in `docs/`
- Check code comments and docstrings
- Review example implementations

### External Resources
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Selenium Documentation](https://selenium-python.readthedocs.io/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [uv Documentation](https://github.com/astral-sh/uv)

### Community
- GitHub Issues
- Stack Overflow (tag: flask, selenium, pandas)

## Next Steps

1. ✅ **Setup complete** - You're ready to develop!
2. 📖 **Read Architecture** - Understand system design
3. 🎯 **Pick a Task** - Check `CODE_IMPROVEMENTS.md`
4. 🧪 **Write Tests** - Add test coverage
5. 🚀 **Deploy** - Ship your features

Happy coding! 🎉
