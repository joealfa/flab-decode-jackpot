# Fortune Lab: Decoding the Jackpot

A comprehensive lottery analysis application that scrapes Philippine PCSO lottery results and provides deep statistical analysis with probability-based predictions.

## Features

- **Automated Data Collection**: Scrapes historical lottery data from PCSO website using Selenium
- **Advanced Analytics**: Statistical analysis of draw patterns, frequencies, and trends
- **Accuracy Tracking**: Compare predictions against actual results and track performance over time
- **Day-Specific Analysis**: Analyze patterns for each day of the week
- **Smart Predictions**: AI-powered combination suggestions based on probability analysis
- **Visual Reports**: Beautiful charts and graphs for easy data understanding
- **Performance Dashboard**: Interactive accuracy analytics with algorithm comparison
- **Modern UI**: Elegant, responsive design for optimal user experience

## Supported Games

- Lotto 6/42
- Mega Lotto 6/45
- Super Lotto 6/49
- Grand Lotto 6/55
- Ultra Lotto 6/58

## Prerequisites

- Python 3.14+
- uv (Python package manager)
- Chrome/Chromium browser (for Selenium)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd flab-decode-jackpot
```

2. Install dependencies using uv:
```bash
uv sync
```

3. The application will automatically download ChromeDriver when first running the scraper.

## Usage

### Running the Application

Start the Flask development server:

```bash
uv run python app.py
```

The application will be available at `http://localhost:5000`

### Using the Web Interface

1. **Home Page**: Select your lottery game type and date range
2. **Generate Analysis**: Click "Generate Analysis" to scrape data from PCSO website
3. **View Dashboard**: Once complete, view comprehensive analysis with:
   - Top 5 predicted combinations
   - Overall statistics and patterns
   - Day-specific analysis
   - Interactive charts and visualizations
4. **Submit Actual Results**: After the draw, submit actual winning numbers to track accuracy
5. **Accuracy Dashboard**: View prediction performance metrics and algorithm comparison at `/accuracy-dashboard`

### API Endpoints

The application provides RESTful API endpoints:

**Core Features:**
- `GET /` - Home page
- `POST /scrape` - Scrape lottery data
- `GET /analyze/<filename>` - View analysis dashboard
- `POST /api/analyze` - Get analysis data as JSON
- `GET /api/files` - List all saved result files
- `POST /api/submit-actual-result` - Submit actual lottery result for accuracy comparison

**Accuracy Analysis:**
- `GET /accuracy-dashboard` - Interactive accuracy dashboard
- `GET /api/accuracy-analysis` - Complete accuracy metrics (supports `?game_type=` filter)
- `GET /api/accuracy-summary` - Quick accuracy summary
- `GET /api/accuracy-files` - List all accuracy comparison files

**System:**
- `GET /health` - Health check endpoint

## Project Structure

```
flab-decode-jackpot/
├── app/
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── scraper.py      # PCSO website scraper
│   │   └── analyzer.py     # Data analysis and predictions
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── dashboard.html
│   │   ├── 404.html
│   │   └── 500.html
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── main.js
│   └── data/               # Scraped data stored here
├── app.py                  # Main Flask application
├── pyproject.toml
├── CLAUDE.md
└── README.md
```

## Analysis Features

### Overall Statistics
- Most/least frequent numbers (hot/cold numbers)
- Even/odd distribution patterns
- High/low number analysis
- Consecutive number patterns
- Sum range analysis

### Prediction Algorithms
- **Top Predictions**: Frequency-based with balance optimization
- **Winning Predictions**: Optimized for historical winner patterns
- **Pattern Predictions**: Consecutive draw pattern analysis
- **Ultimate Predictions**: Multi-dimensional comprehensive analysis

### Accuracy Tracking
- **Performance Metrics**: Track prediction accuracy over time
- **Algorithm Comparison**: Compare effectiveness of different prediction methods
- **Match Distribution**: Analyze number of correct predictions (0-6 matches)
- **Best Performances**: Historical best matches achieved
- **Game-Specific Stats**: Performance breakdown by lottery game type

### Day-Specific Analysis
- Patterns for Monday through Sunday
- Day-specific hot numbers
- Top 5 predictions per day

### Visualizations
- Number frequency bar chart
- Sum distribution line chart
- Even/odd pattern pie chart
- Day of week distribution

## Configuration

The application uses the following default settings:

- **Data Path**: `app/data/`
- **Date Range**: Dynamically determined from available years on the PCSO website
- **Headless Browser**: Enabled (can be changed in scraper initialization)

## Important Notes

- Web scraping may take several minutes depending on the date range
- Ensure stable internet connection for scraping
- Chrome browser is required for Selenium WebDriver
- Results are saved as JSON files in `app/data/` directory

## Disclaimer

This application is for entertainment and educational purposes only. Past lottery results do not guarantee future outcomes. Use at your own discretion.

## License

MIT License

## Support

For issues, questions, or contributions, please refer to the project repository.
