"""
Test script to verify date range validation in scraper.
"""
import logging
from datetime import datetime
from app.modules.scraper import PCSOScraper
from app.exceptions import DateRangeException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_date_validation():
    """Test that date validation works correctly."""
    logger.info("=" * 60)
    logger.info("Testing Date Range Validation")
    logger.info("=" * 60)
    
    scraper = PCSOScraper(headless=True)
    
    # Test 1: Get available date range
    logger.info("\nTest 1: Getting available date range from PCSO website...")
    try:
        date_range = scraper.get_available_date_range()
        logger.info(f"✓ Available date range: {date_range['min_year']} to {date_range['max_year']}")
    except Exception as e:
        logger.error(f"✗ Failed to get date range: {str(e)}")
        return
    finally:
        if scraper.driver:
            scraper.driver.quit()
    
    # Test 2: Try scraping with invalid date (too old)
    logger.info("\nTest 2: Testing with year 2015 (should fail gracefully)...")
    scraper = PCSOScraper(headless=True)
    try:
        result = scraper.scrape_lottery_data(
            game_type="Lotto 6/42",
            start_date=datetime(2015, 1, 1),
            end_date=datetime(2015, 1, 31),
            save_path="app/data"
        )
        logger.error("✗ Test failed - should have raised DateRangeException")
    except DateRangeException as e:
        logger.info(f"✓ DateRangeException raised correctly: {e.message}")
        logger.info(f"  Details: {e.details}")
    except Exception as e:
        logger.error(f"✗ Wrong exception type: {type(e).__name__}: {str(e)}")
    finally:
        if scraper.driver:
            scraper.driver.quit()
    
    # Test 3: Try with valid date
    logger.info("\nTest 3: Testing with year 2024 (should work)...")
    scraper = PCSOScraper(headless=True)
    try:
        result = scraper.scrape_lottery_data(
            game_type="Lotto 6/42",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 5),
            save_path="app/data"
        )
        logger.info(f"✓ Scraping succeeded: {result.get('total_draws', 0)} draws")
    except Exception as e:
        logger.error(f"✗ Unexpected error: {str(e)}")
    finally:
        if scraper.driver:
            scraper.driver.quit()
    
    logger.info("\n" + "=" * 60)
    logger.info("Testing Complete")
    logger.info("=" * 60)

if __name__ == "__main__":
    test_date_validation()
