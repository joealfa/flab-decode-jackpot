# Accuracy Analysis Documentation

## Overview

The **Accuracy Analysis** module provides comprehensive tracking and evaluation of lottery prediction performance. It compares predicted numbers against actual draw results to measure algorithm effectiveness.

## Features

### 1. Comprehensive Metrics
- **Total Submissions**: Number of actual results submitted for comparison
- **Total Predictions**: Count of all predictions evaluated
- **Average Matches**: Mean number of correct predictions per attempt
- **Jackpot Hits**: Predictions that matched all 6 numbers

### 2. Algorithm Performance Comparison
Track performance across three prediction algorithms:
- **Top Predictions**: Frequency-based with balance optimization
- **Winning Predictions**: Optimized for winner patterns
- **Pattern Predictions**: Consecutive draw analysis

### 3. Best Performance Tracking
- Overall best match across all predictions
- Best performance per algorithm type
- Historical performance tracking

### 4. Match Distribution Analysis
Breakdown of predictions by number of matches (0-6):
- Visual distribution charts
- Percentage calculations
- Count statistics

### 5. Game-Specific Breakdown
Performance metrics separated by lottery game type:
- Lotto 6/42
- Mega Lotto 6/45
- Super Lotto 6/49
- Grand Lotto 6/55
- Ultra Lotto 6/58

## Usage

### API Endpoints

#### Get Complete Analysis
```http
GET /api/accuracy-analysis?game_type={game_type}
```

**Parameters:**
- `game_type` (optional): Filter by specific game (e.g., "Lotto 6/42")

**Response:**
```json
{
  "success": true,
  "data": {
    "total_submissions": 10,
    "game_type": "Lotto 6/42",
    "analysis_date": "2025-10-30T12:00:00",
    "prediction_types": {
      "top_predictions": {
        "total_predictions": 50,
        "avg_matches_per_prediction": 2.5,
        "jackpot_hits": 0,
        "five_number_hits": 1,
        "match_distribution": {...}
      },
      "winning_predictions": {...},
      "pattern_predictions": {...}
    },
    "best_performances": {...},
    "match_distribution": {...},
    "recent_accuracy": [...],
    "game_breakdown": {...},
    "best_algorithm": {
      "name": "Top Predictions",
      "avg_matches": 2.5,
      "jackpot_hits": 0
    }
  }
}
```

#### Get Quick Summary
```http
GET /api/accuracy-summary?game_type={game_type}
```

**Parameters:**
- `game_type` (optional): Filter by specific game

**Response:**
```json
{
  "success": true,
  "data": {
    "total_submissions": 10,
    "game_type": "All Games",
    "best_algorithm": {
      "name": "Top Predictions",
      "avg_matches": 2.5,
      "jackpot_hits": 0,
      "five_number_hits": 2
    },
    "overall_stats": {
      "avg_matches": 2.3,
      "total_predictions": 150,
      "jackpot_hits": 0,
      "five_number_hits": 3
    },
    "best_performance": {
      "matches": 5,
      "details": {...}
    }
  }
}
```

#### List Accuracy Files
```http
GET /api/accuracy-files?game_type={game_type}
```

**Response:**
```json
{
  "success": true,
  "total": 10,
  "data": [
    {
      "filename": "accuracy_Lotto_6-42_20251030_120000.json",
      "game_type": "Lotto 6/42",
      "draw_date": "2025-10-30",
      "actual_numbers": [5, 12, 23, 31, 38, 42],
      "timestamp": "20251030_120000"
    }
  ]
}
```

### Dashboard Access

Visit `/accuracy-dashboard` to view the interactive accuracy dashboard with:
- Summary cards showing key metrics
- Best algorithm performance
- Match distribution charts
- Algorithm performance comparison charts
- Game-specific breakdown tables
- Recent submissions history
- Best performances across all algorithms

### Programmatic Usage

```python
from app.modules.accuracy_analyzer import AccuracyAnalyzer

# Initialize analyzer
analyzer = AccuracyAnalyzer()

# Get complete analysis for all games
analysis = analyzer.analyze_overall_accuracy()

# Get analysis for specific game
lotto_analysis = analyzer.analyze_overall_accuracy("Lotto 6/42")

# Get quick summary
summary = analyzer.get_accuracy_summary()

# Load all accuracy files
files = analyzer.load_all_accuracy_files()

# Filter by game type
lotto_files = analyzer.load_all_accuracy_files("Lotto 6/42")
```

## File Storage

Accuracy comparison files are stored in:
```
app/data/accuracy/accuracy_{game_slug}_{timestamp}.json
```

**Filename Format:**
- `game_slug`: Game name with underscores and hyphens (e.g., `Lotto_6-42`)
- `timestamp`: `YYYYMMDD_HHMMSS` format

**Example:**
```
accuracy_Lotto_6-42_20251030_153045.json
```

## Accuracy File Structure

```json
{
  "actual_numbers": [5, 12, 23, 31, 38, 42],
  "draw_date": "2025-10-30",
  "game_type": "Lotto 6/42",
  "filename": "accuracy_Lotto_6-42_20251030_153045.json",
  "timestamp": "20251030_153045",
  "top_predictions_comparison": [
    {
      "rank": 1,
      "predicted_numbers": [5, 12, 19, 31, 38, 42],
      "matches": 5,
      "confidence_score": 85.5
    }
  ],
  "winning_predictions_comparison": [...],
  "pattern_predictions_comparison": [...]
}
```

## Metrics Explanation

### Average Matches
The mean number of correctly predicted numbers per prediction attempt. Range: 0-6.

**Example:**
- 3 predictions: [3 matches, 2 matches, 4 matches]
- Average: (3 + 2 + 4) / 3 = 3.0

### Match Distribution
Breakdown showing how many predictions achieved each match count:
- **0 Matches**: Complete miss
- **1 Match**: 1 correct number
- **2 Matches**: 2 correct numbers
- **3 Matches**: 3 correct numbers (common prize tier)
- **4 Matches**: 4 correct numbers (higher prize tier)
- **5 Matches**: 5 correct numbers (major prize)
- **6 Matches**: Jackpot!

### Rank Performance
Performance analysis based on prediction ranking:
- **Rank 1**: Top prediction performance
- **Rank 2**: Second prediction performance
- **Rank 3**: Third prediction performance
- And so on...

Higher-ranked predictions should ideally perform better, indicating algorithm quality.

## Interpretation Guide

### Good Performance Indicators
✅ **Average matches ≥ 2.0**: Above random chance  
✅ **Consistent rank performance**: Rank 1 outperforms lower ranks  
✅ **5-number hits**: Demonstrates strong prediction capability  
✅ **Low 0-match rate**: Fewer complete misses  

### Areas for Improvement
⚠️ **Average matches < 1.5**: Below statistical expectation  
⚠️ **Inverse rank performance**: Lower ranks perform better  
⚠️ **High 0-match rate**: Too many complete misses  
⚠️ **No 4+ matches**: Algorithms need refinement  

## Best Practices

### 1. Submit Actual Results Promptly
Submit actual draw results as soon as they're available for accurate tracking.

### 2. Review Algorithm Performance Regularly
Check the accuracy dashboard weekly to identify trends and patterns.

### 3. Compare Across Games
Different lottery games may favor different algorithms. Compare performance across games.

### 4. Consider Sample Size
More submissions provide more reliable accuracy metrics. Aim for at least 10 submissions per game.

### 5. Track Trends Over Time
Monitor whether accuracy improves as more historical data is collected.

## Error Handling

### No Accuracy Data
```json
{
  "success": false,
  "error": "No accuracy data found",
  "error_code": 404,
  "details": {
    "game_type": "Lotto 6/42"
  }
}
```

**Solution:** Submit actual lottery results via the analysis dashboard.

### Invalid Game Type
Filter will return empty results if game type doesn't match any files.

## Limitations

### Statistical Reality
- Lottery draws are random events
- Past performance doesn't guarantee future results
- High accuracy doesn't ensure jackpot wins
- Predictions are probabilistic, not deterministic

### Sample Size
- Small sample sizes may show misleading patterns
- At least 10 submissions recommended per game
- More submissions = more reliable metrics

### Algorithm Constraints
- All algorithms are heuristic-based
- No algorithm can predict truly random events
- Performance varies by game type and historical data quality

## Future Enhancements

Potential improvements to the accuracy analysis module:

1. **Time-Series Analysis**: Track accuracy trends over time
2. **Confidence Intervals**: Statistical confidence for metrics
3. **Comparative Analysis**: Compare against random selection baseline
4. **Machine Learning Integration**: Use accuracy data to train ML models
5. **Export Functionality**: Download accuracy reports as CSV/PDF
6. **Alerts**: Notify when accuracy drops below thresholds

## Technical Details

### Module: `app/modules/accuracy_analyzer.py`

**Main Class:** `AccuracyAnalyzer`

**Key Methods:**
- `load_all_accuracy_files(game_type)`: Load accuracy comparison files
- `analyze_overall_accuracy(game_type)`: Complete accuracy analysis
- `get_accuracy_summary(game_type)`: Quick summary metrics
- `_analyze_prediction_type(files, key)`: Analyze specific prediction type
- `_find_best_performances(files)`: Find top performances
- `_calculate_match_distribution(files)`: Calculate match statistics
- `_calculate_recent_accuracy(files, limit)`: Recent submission analysis
- `_calculate_game_breakdown(files)`: Per-game statistics
- `_determine_best_algorithm(types)`: Identify best algorithm

### Dependencies
- Python 3.14+
- Flask 3.1.2
- app.config
- app.exceptions

## Examples

### Example 1: View Overall Accuracy
```python
analyzer = AccuracyAnalyzer()
analysis = analyzer.analyze_overall_accuracy()
print(f"Total submissions: {analysis['total_submissions']}")
print(f"Best algorithm: {analysis['best_algorithm']['name']}")
print(f"Average matches: {analysis['match_distribution']['average_matches']}")
```

### Example 2: Compare Algorithms
```python
analysis = analyzer.analyze_overall_accuracy("Lotto 6/42")
types = analysis['prediction_types']

for algo_name, metrics in types.items():
    print(f"{algo_name}: {metrics['avg_matches_per_prediction']} avg matches")
```

### Example 3: Find Best Performance
```python
analysis = analyzer.analyze_overall_accuracy()
best = analysis['best_performances']['highest_matches']

print(f"Best match: {best['matches']} numbers")
print(f"Date: {best['details']['draw_date']}")
print(f"Game: {best['details']['game_type']}")
```

## Responsible Gaming Reminder

The accuracy analysis is designed for:
- ✅ Educational purposes
- ✅ Understanding lottery statistics
- ✅ Comparing prediction algorithms
- ✅ Entertainment value

It is **NOT** designed for:
- ❌ Guaranteeing lottery wins
- ❌ Investment strategies
- ❌ Professional gambling
- ❌ Financial planning

**Remember:** Lotteries are games of chance. Play responsibly within your means.

## Support

For issues or questions about accuracy analysis:
1. Check this documentation
2. Review API error messages
3. Verify accuracy files exist in `app/data/accuracy/`
4. Check application logs in `logs/` directory
5. Review code in `app/modules/accuracy_analyzer.py`

---

**Version:** 1.0.0  
**Last Updated:** October 30, 2025  
**Author:** Fortune Lab Team
