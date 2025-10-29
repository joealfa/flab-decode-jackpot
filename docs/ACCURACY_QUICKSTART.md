# Accuracy Analysis - Quick Start Guide

## What is the Accuracy Folder?

The `app/data/accuracy/` folder stores **accuracy comparison results** when you submit actual lottery draw results to compare against Fortune Lab's predictions.

## How It Works

### 1. Generate Predictions
First, scrape lottery data and generate analysis with predictions:
```
1. Scrape lottery data for a game
2. Analyze the results
3. Get predictions (Top, Winning, Pattern)
```

### 2. Submit Actual Results
After the actual lottery draw occurs:
```
1. Open the Analysis Dashboard
2. Find "Submit Actual Result" section
3. Enter:
   - Actual winning numbers
   - Draw date
   - Jackpot amount (optional)
   - Number of winners (optional)
4. Click Submit
```

### 3. View Accuracy Comparison
The system automatically:
- Compares actual numbers vs. all predictions
- Counts how many numbers matched
- Saves results to `app/data/accuracy/`
- Shows immediate comparison results

### 4. View Accuracy Dashboard
Visit the **Accuracy Dashboard** to see:
- Overall prediction performance
- Best performing algorithm
- Match distribution charts
- Historical accuracy trends
- Best matches ever achieved

## Quick Access

### Dashboard URL
```
http://localhost:5000/accuracy-dashboard
```

### API Endpoints
```bash
# Get full analysis
GET http://localhost:5000/api/accuracy-analysis

# Get quick summary
GET http://localhost:5000/api/accuracy-summary

# List all accuracy files
GET http://localhost:5000/api/accuracy-files

# Filter by game type
GET http://localhost:5000/api/accuracy-analysis?game_type=Lotto%206/42
```

## Example Workflow

**Step 1: Scrape Data**
```
Game: Lotto 6/42
End Date: 2025-10-29
```

**Step 2: Analyze**
View analysis dashboard, get predictions like:
- Top Prediction #1: [5, 12, 19, 28, 35, 41]
- Winning Prediction #1: [3, 15, 22, 29, 36, 40]
- Pattern Prediction #1: [8, 14, 21, 30, 37, 42]

**Step 3: Actual Draw Occurs**
Actual winning numbers: [5, 12, 19, 31, 38, 42]

**Step 4: Submit Result**
Enter the actual numbers via the dashboard.

**Step 5: See Comparison**
System shows:
- Top Prediction #1: **4 matches** ✅ (5, 12, 19, 42)
- Winning Prediction #1: 0 matches
- Pattern Prediction #1: 1 match (42)

**Step 6: View Analytics**
Check Accuracy Dashboard for comprehensive stats.

## What Gets Analyzed?

### Prediction Types
1. **Top Predictions** (5 predictions)
   - Frequency-based with balance
   - Analyzed individually

2. **Winning Predictions** (5 predictions)
   - Optimized for winner patterns
   - Analyzed individually

3. **Pattern Predictions** (5 predictions)
   - Consecutive draw analysis
   - Analyzed individually

### Match Counts
- **6 matches** = Jackpot! 🎉
- **5 matches** = Excellent prediction
- **4 matches** = Very good
- **3 matches** = Good (typical prize tier)
- **2 matches** = Fair
- **1 match** = Poor
- **0 matches** = Complete miss

### Metrics Tracked
- Total submissions
- Total predictions tested
- Average matches per prediction
- Match distribution (0-6 matches)
- Best performance ever
- Best performance per algorithm
- Performance by game type
- Recent accuracy trends

## Dashboard Features

### Summary Cards
- Total Submissions
- Total Predictions
- Average Matches
- Jackpot Hits (6/6 matches)

### Best Algorithm Card
Shows which algorithm performs best:
- Algorithm name
- Average matches
- Jackpot hits
- 5-number hits

### Charts
1. **Match Distribution Bar Chart**
   - Visual breakdown of match counts
   - 0 matches through 6 matches
   - Total prediction count

2. **Algorithm Performance Chart**
   - Compares Top vs. Winning vs. Pattern
   - Average matches per algorithm
   - Side-by-side comparison

### Tables
1. **Performance by Game Type**
   - Submissions per game
   - Total predictions
   - Average matches
   - Best match achieved

2. **Recent Submissions**
   - Last 10 submissions
   - Draw date and game
   - Actual numbers
   - Best match achieved
   - Best algorithm for that draw

### Best Performance Cards
- **Overall Best**: Highest match across all
- **Top Predictions Best**: Best from Top algorithm
- **Winning Predictions Best**: Best from Winning algorithm
- **Pattern Predictions Best**: Best from Pattern algorithm

## File Format

Accuracy files are stored as:
```
accuracy_{game_slug}_{timestamp}.json
```

Example:
```
accuracy_Lotto_6-42_20251030_153045.json
```

Content structure:
```json
{
  "actual_numbers": [5, 12, 23, 31, 38, 42],
  "draw_date": "2025-10-30",
  "game_type": "Lotto 6/42",
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

## Tips for Better Analysis

### 1. Submit Regularly
Submit actual results for every draw you predicted to build comprehensive accuracy data.

### 2. Track Multiple Games
Analyze all lottery games to see which games and algorithms perform best.

### 3. Review Trends
Check the dashboard weekly to identify patterns and trends.

### 4. Compare Algorithms
Different games may favor different algorithms. Use accuracy data to choose wisely.

### 5. Build History
The more data you have, the more reliable the accuracy metrics become.

## Understanding the Results

### Random Baseline
In a 6/42 lottery:
- Matching 0-1 numbers: Expected by chance
- Matching 2 numbers: Slightly better than chance
- Matching 3+ numbers: Indicates prediction quality
- Matching 5-6 numbers: Exceptional (but still rare)

### Algorithm Quality
- **Average ≥ 2.0**: Good algorithm performance
- **Average 1.5-2.0**: Acceptable performance
- **Average < 1.5**: Consider algorithm improvements
- **Any 5-6 matches**: Algorithm shows promise

### Sample Size Matters
- **< 5 submissions**: Too early to judge
- **5-10 submissions**: Initial patterns emerging
- **10-20 submissions**: Moderate confidence
- **20+ submissions**: Strong statistical basis

## Common Questions

**Q: Why are accuracy files empty initially?**  
A: You need to submit actual lottery results first. The folder is created but empty until you submit data.

**Q: How do I submit actual results?**  
A: Open any analysis dashboard and scroll to "Submit Actual Result" section.

**Q: Can I delete old accuracy files?**  
A: Yes, but they won't appear in analytics. Consider archiving instead.

**Q: What if I make a mistake?**  
A: You can delete the incorrect accuracy file from `app/data/accuracy/` folder.

**Q: Does high accuracy guarantee wins?**  
A: No! Lotteries are random. Accuracy tracking is educational, not predictive of future results.

## Navigation

- **Home**: `/` - Main scraping interface
- **Accuracy Dashboard**: `/accuracy-dashboard` - View accuracy analytics
- **Analysis Dashboard**: `/dashboard` - View lottery analysis
- **API Docs**: See `docs/ACCURACY_ANALYSIS.md`

## Support

For detailed technical documentation, see:
- `docs/ACCURACY_ANALYSIS.md` - Complete API and usage guide
- `app/modules/accuracy_analyzer.py` - Source code
- Application logs: `logs/app.log`

---

**Remember:** This is for educational purposes only. Lottery draws are random events. Past performance doesn't guarantee future results. Play responsibly! 🎲
