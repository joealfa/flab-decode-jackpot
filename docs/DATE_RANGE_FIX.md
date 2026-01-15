# Date Range Validation Fix

## Issue
Application was crashing with `NoSuchElementException` when users tried to scrape data from years not available on the PCSO website (e.g., 2015).

## Root Cause
The PCSO website dropdown only contains a limited range of years (typically 2016-present). When the scraper tried to select year "2015", Selenium couldn't find that option and threw an exception.

## Solution

### 1. Custom Exception
Created `DateRangeException` in [app/exceptions.py](../app/exceptions.py):
- Provides structured error information
- Includes both requested and available date ranges
- Enables better error handling throughout the application

### 2. Year Validation in Scraper
Modified [app/modules/scraper.py](../app/modules/scraper.py):

#### Early Validation (Line ~420)
- Checks available years immediately after page loads
- Validates date range before starting scraping process
- Fails fast with helpful error message

#### Selection Validation (Line ~225)
- Validates year availability before attempting dropdown selection
- Provides detailed error message with available year range
- Prevents NoSuchElementException from propagating

#### Utility Method (Line ~265)
- Added `get_available_date_range()` method
- Can be called independently to check PCSO website limits
- Returns dict with `min_year` and `max_year`

### 3. UI Improvement
Updated default start date in [app/templates/index.html](../app/templates/index.html):
- Changed from 2015-01-01 to 2020-01-01
- Reduces likelihood of users encountering the error
- Still allows manual date selection

## Error Messages

### Before Fix
```
NoSuchElementException: Message: Cannot locate option with value: 2015
```

### After Fix
```
DateRangeException: Requested date range (2015 to 2015) is outside 
available range on PCSO website (2016 to 2026). Please adjust your date range.

Details: {
  'requested_start_year': 2015,
  'requested_end_year': 2015,
  'available_min_year': 2016,
  'available_max_year': 2026
}
```

## Testing

Run the test script to verify:
```bash
uv run python test_date_validation.py
```

Expected behavior:
1. ✓ Successfully retrieves available date range
2. ✓ Raises DateRangeException for year 2015
3. ✓ Successfully scrapes data for valid year (2024)

## Implementation Details

### Files Modified
- `app/exceptions.py` - Added DateRangeException class
- `app/modules/scraper.py` - Added validation logic
- `app/templates/index.html` - Updated default start date

### Backward Compatibility
- ✓ No breaking changes to API
- ✓ Existing error handling in Flask routes works automatically
- ✓ Custom exception inherits from base ScraperException

### Performance Impact
- Minimal: One additional check during page load (~0.1s)
- Benefit: Prevents wasted time on invalid scraping attempts

## Best Practices Followed
- ✅ Custom exceptions for domain-specific errors
- ✅ Early validation to fail fast
- ✅ Comprehensive logging
- ✅ Type hints and docstrings
- ✅ User-friendly error messages
- ✅ Structured exception details for debugging

## Future Enhancements
Consider adding:
1. Dynamic year range fetching for date picker UI
2. Caching of available date range (changes infrequently)
3. API endpoint to query available date range
4. Frontend validation before submission

## Related Documentation
- [AI Instructions](AI_INSTRUCTIONS.md)
- [Architecture](ARCHITECTURE.md)
- [Developer Guide](DEVELOPER_GUIDE.md)
