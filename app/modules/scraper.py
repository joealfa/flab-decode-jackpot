"""
PCSO Lottery Data Scraper Module
Extracts lottery draw results from PCSO website using Selenium.
"""

import json
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PCSOScraper:
    """Scrapes lottery results from PCSO website."""

    PCSO_URL = "https://www.pcso.gov.ph/SearchLottoResult.aspx"

    # Game type mapping for the website dropdown
    GAME_TYPES = {
        "Lotto 6/42": "Lotto 6/42",
        "Mega Lotto 6/45": "Mega Lotto 6/45",
        "Super Lotto 6/49": "Super Lotto 6/49",
        "Grand Lotto 6/55": "Grand Lotto 6/55",
        "Ultra Lotto 6/58": "Ultra Lotto 6/58"
    }

    # Element IDs from PCSO website
    SELECTORS = {
        'start_month': 'cphContainer_cpContent_ddlStartMonth',
        'start_date': 'cphContainer_cpContent_ddlStartDate',
        'start_year': 'cphContainer_cpContent_ddlStartYear',
        'end_month': 'cphContainer_cpContent_ddlEndMonth',
        'end_date': 'cphContainer_cpContent_ddlEndDay',
        'end_year': 'cphContainer_cpContent_ddlEndYear',
        'game_type': 'cphContainer_cpContent_ddlSelectGame',
        'search_button': 'cphContainer_cpContent_btnSearch'
    }

    def __init__(self, headless: bool = True):
        """
        Initialize the scraper with Chrome WebDriver.

        Args:
            headless: Run browser in headless mode (no GUI)
        """
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None

    def _setup_driver(self) -> webdriver.Chrome:
        """Set up and return Chrome WebDriver."""
        logger.info("Setting up Chrome WebDriver...")
        chrome_options = Options()

        # Chromium binary path for WSL/Linux
        chrome_options.binary_location = '/usr/bin/chromium-browser'

        if self.headless:
            chrome_options.add_argument('--headless=new')  # Use new headless mode
            logger.info("Running in headless mode")

        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')

        # Add more stability options
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # Additional options for WSL
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--remote-debugging-port=9222')

        # Use system chromedriver
        chromedriver_path = '/usr/bin/chromedriver'
        logger.info(f"Using system ChromeDriver: {chromedriver_path}")

        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Set page load timeout
        driver.set_page_load_timeout(30)

        logger.info("Chrome WebDriver initialized successfully")
        return driver

    def _select_date(self, month: int, day: int, year: int, prefix: str) -> None:
        """
        Select date from dropdowns.

        Args:
            month: Month (1-12)
            day: Day (1-31)
            year: Year (e.g., 2015)
            prefix: 'start' or 'end'
        """
        # Month names mapping
        month_names = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April',
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }

        month_name = month_names[month]
        logger.info(f"Selecting {prefix} date: {month_name} {day}, {year}")

        # Select month by visible text (month name)
        month_select = Select(self.driver.find_element(By.ID, self.SELECTORS[f'{prefix}_month']))
        month_select.select_by_visible_text(month_name)
        logger.debug(f"  Selected month: {month_name}")
        time.sleep(0.5)

        # Select day
        day_select = Select(self.driver.find_element(By.ID, self.SELECTORS[f'{prefix}_date']))
        day_select.select_by_value(str(day))
        logger.debug(f"  Selected day: {day}")
        time.sleep(0.5)

        # Select year
        year_select = Select(self.driver.find_element(By.ID, self.SELECTORS[f'{prefix}_year']))
        year_select.select_by_value(str(year))
        logger.debug(f"  Selected year: {year}")
        time.sleep(0.5)

    def scrape_lottery_data(
        self,
        game_type: str,
        start_date: datetime,
        end_date: datetime,
        save_path: str = "app/data"
    ) -> Dict:
        """
        Scrape lottery results from PCSO website.

        Args:
            game_type: Type of lottery game
            start_date: Start date for results
            end_date: End date for results
            save_path: Directory to save results

        Returns:
            Dictionary containing scraped results and metadata
        """
        logger.info("="*60)
        logger.info(f"Starting lottery data scraping")
        logger.info(f"Game Type: {game_type}")
        logger.info(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        logger.info("="*60)

        if game_type not in self.GAME_TYPES:
            error_msg = f"Invalid game type. Must be one of: {list(self.GAME_TYPES.keys())}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Check if file already exists
        game_slug = game_type.replace(' ', '_').replace('/', '-')
        date_str = end_date.strftime('%Y%m%d')
        filename = f"result_{game_slug}_{date_str}.json"
        filepath = os.path.join(save_path, filename)

        if os.path.exists(filepath):
            logger.info(f"Data file already exists: {filename}")
            logger.info("Loading existing data instead of scraping...")

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Ensure filename is in the data
                if 'filename' not in data:
                    data['filename'] = filename

                # Mark as cached
                data['cached'] = True

                logger.info(f"Loaded {data.get('total_draws', 0)} existing draws from file")
                logger.info("="*60)
                logger.info("Using cached data (no scraping needed)")
                logger.info("="*60)
                return data

            except Exception as e:
                logger.warning(f"Error loading existing file: {str(e)}")
                logger.info("Will proceed with scraping...")

        try:
            # Set up driver
            logger.info("Step 1: Setting up WebDriver...")
            self.driver = self._setup_driver()

            logger.info(f"Step 2: Navigating to PCSO website: {self.PCSO_URL}")
            self.driver.get(self.PCSO_URL)

            # Wait for page to load
            logger.info("Step 3: Waiting for page to load...")
            wait = WebDriverWait(self.driver, 30)
            wait.until(EC.presence_of_element_located((By.ID, self.SELECTORS['game_type'])))
            logger.info("Page loaded successfully")

            # Select game type
            logger.info(f"Step 4: Selecting game type: {game_type}")
            game_select = Select(self.driver.find_element(By.ID, self.SELECTORS['game_type']))
            game_select.select_by_visible_text(self.GAME_TYPES[game_type])
            logger.info(f"Game type '{game_type}' selected")
            time.sleep(1)

            # Select start date
            logger.info("Step 5: Selecting start date...")
            self._select_date(start_date.month, start_date.day, start_date.year, 'start')

            # Select end date
            logger.info("Step 6: Selecting end date...")
            self._select_date(end_date.month, end_date.day, end_date.year, 'end')

            # Click search button
            logger.info("Step 7: Clicking search button...")
            search_button = self.driver.find_element(By.ID, self.SELECTORS['search_button'])
            search_button.click()
            logger.info("Search button clicked, waiting for results...")

            # Wait for results to load with better timeout handling
            logger.info("Step 8: Waiting for results table to load...")
            time.sleep(3)  # Initial wait for page to start processing

            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.search-lotto-result-div table')))
                logger.info("Results table loaded successfully")
            except TimeoutException:
                logger.warning("Results table not found, trying alternative selector...")
                # Try to get page source for debugging
                logger.debug(f"Current URL: {self.driver.current_url}")
                logger.error("Could not find results table on the page")
                raise

            # Extract results
            logger.info("Step 9: Extracting lottery results from table...")
            results = self._extract_results()
            logger.info(f"Successfully extracted {len(results)} lottery draws")

            # Prepare data structure
            data = {
                'game_type': game_type,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'total_draws': len(results),
                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'results': results
            }

            # Save to JSON file
            logger.info("Step 10: Saving results to JSON file...")
            filename = self._save_results(data, game_type, end_date, save_path)
            data['filename'] = filename
            logger.info(f"Results saved to: {filename}")

            logger.info("="*60)
            logger.info("Scraping completed successfully!")
            logger.info("="*60)

            return data

        except TimeoutException as e:
            error_msg = f"Timeout while loading PCSO website: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except NoSuchElementException as e:
            error_msg = f"Could not find element on page: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error scraping data: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)
        finally:
            if self.driver:
                logger.info("Closing WebDriver...")
                try:
                    self.driver.quit()
                except Exception as e:
                    # Ignore SSL errors during cleanup (Python 3.14 RC2 bug)
                    logger.warning(f"Error closing driver (ignoring): {str(e)}")

    def _extract_results(self) -> List[Dict]:
        """
        Extract lottery results from the results table.

        PCSO table format:
        LOTTO GAME | COMBINATIONS | DRAW DATE | JACKPOT (PHP) | WINNERS
        """
        results = []

        try:
            # Find the results table
            logger.info("Locating results table...")
            table = self.driver.find_element(By.CSS_SELECTOR, '.search-lotto-result-div table tbody')
            rows = table.find_elements(By.TAG_NAME, 'tr')
            logger.info(f"Found {len(rows)} rows in results table")

            for idx, row in enumerate(rows, 1):
                cols = row.find_elements(By.TAG_NAME, 'td')

                # PCSO table: LOTTO GAME (0), COMBINATIONS (1), DRAW DATE (2), JACKPOT (3), WINNERS (4)
                if len(cols) >= 3:
                    # Extract game type (column 0)
                    game_name = cols[0].text.strip() if len(cols) > 0 else ""

                    # Extract winning numbers (column 1)
                    numbers_text = cols[1].text.strip()
                    # Split by hyphen and clean up
                    numbers = [int(num.strip()) for num in numbers_text.split('-') if num.strip().isdigit()]

                    # Extract draw date (column 2)
                    draw_date = cols[2].text.strip()

                    # Extract jackpot (column 3, if available)
                    jackpot = cols[3].text.strip() if len(cols) > 3 else "N/A"

                    # Extract winners (column 4, if available)
                    winners = cols[4].text.strip() if len(cols) > 4 else "N/A"

                    # Parse date to get day of week
                    try:
                        date_obj = datetime.strptime(draw_date, '%m/%d/%Y')
                        day_of_week = date_obj.strftime('%A')
                    except ValueError:
                        # Try alternative date format
                        try:
                            date_obj = datetime.strptime(draw_date, '%Y-%m-%d')
                            day_of_week = date_obj.strftime('%A')
                        except ValueError:
                            day_of_week = "Unknown"

                    result = {
                        'game': game_name,
                        'date': draw_date,
                        'day_of_week': day_of_week,
                        'numbers': sorted(numbers),  # Sort numbers for consistency
                        'jackpot': jackpot,
                        'winners': winners
                    }

                    results.append(result)

                    # Log progress every 50 rows
                    if idx % 50 == 0:
                        logger.info(f"Processed {idx}/{len(rows)} rows...")

            logger.info(f"Successfully extracted {len(results)} lottery results")
            return results

        except Exception as e:
            error_msg = f"Error extracting results from table: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def _save_results(
        self,
        data: Dict,
        game_type: str,
        end_date: datetime,
        save_path: str
    ) -> str:
        """
        Save results to JSON file.

        Args:
            data: Data to save
            game_type: Type of game
            end_date: End date for filename
            save_path: Directory to save file

        Returns:
            Filename of saved file
        """
        # Create data directory if it doesn't exist
        logger.info(f"Creating data directory: {save_path}")
        os.makedirs(save_path, exist_ok=True)

        # Create filename
        game_slug = game_type.replace(' ', '_').replace('/', '-')
        date_str = end_date.strftime('%Y%m%d')
        filename = f"result_{game_slug}_{date_str}.json"
        filepath = os.path.join(save_path, filename)

        logger.info(f"Saving results to: {filepath}")

        # Save to JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"File saved successfully: {filename}")
        return filename

    def load_results(self, filename: str, data_path: str = "app/data") -> Dict:
        """
        Load results from JSON file.

        Args:
            filename: Name of the JSON file
            data_path: Directory where file is stored

        Returns:
            Dictionary containing lottery results
        """
        filepath = os.path.join(data_path, filename)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Results file not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return data
