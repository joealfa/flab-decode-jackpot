"""Background jobs that run independently of the Flask request context."""

import logging
from datetime import datetime
from threading import BoundedSemaphore, Semaphore
from typing import Any

import httpx

from app.config import Config
from app.modules.progress_tracker import ProgressTracker
from app.modules.scraper import PCSOScraper
from app.services.ai_history import (
    complete_ai_analysis,
    fail_ai_analysis,
    mark_ai_analysis_running,
)

logger = logging.getLogger(__name__)


def ai_failure_message(error: BaseException, timeout: int) -> str:
    """Translate a model failure into a message that is safe to show users."""
    cause: BaseException | None = error
    while cause is not None:
        if isinstance(cause, httpx.TimeoutException):
            return (
                f"The AI model did not respond within {timeout} seconds. "
                "Try again, or increase OLLAMA_TIMEOUT."
            )
        if isinstance(cause, httpx.ConnectError):
            return "Could not connect to Ollama. Make sure it is running."
        cause = cause.__cause__
    return "AI analysis failed. Check server logs for details."


def ai_analysis_thread(
    ai_dir: str,
    ai_filename: str,
    analysis_data: dict,
    analyzer: Any,
    semaphore: Semaphore,
    timeout: int,
) -> None:
    """Run one queued AI interpretation and persist its outcome."""
    # Waiting here keeps later requests queued behind the local model.
    with semaphore:
        try:
            if not mark_ai_analysis_running(ai_dir, ai_filename):
                return
            logger.info("Starting AI analysis %s", ai_filename)
            result = analyzer.analyze_lottery_report(analysis_data)
            if complete_ai_analysis(ai_dir, ai_filename, result):
                logger.info("AI analysis %s completed", ai_filename)
        except Exception as e:
            logger.error("AI analysis %s failed", ai_filename, exc_info=True)
            try:
                fail_ai_analysis(ai_dir, ai_filename, ai_failure_message(e, timeout))
            except Exception:
                logger.error(
                    "Could not record failure for %s", ai_filename, exc_info=True
                )


def scrape_data_thread(
    task_id: str,
    game_type: str,
    start_date: datetime,
    end_date: datetime,
    data_path: str,
    tracker: ProgressTracker,
    semaphore: BoundedSemaphore,
    settings: Config,
) -> None:
    """Background thread for scraping data."""
    try:
        tracker.create_task(task_id)
        tracker.update_progress(task_id, 0, 100, "Initializing scraper...")

        scraper = PCSOScraper(
            headless=settings.HEADLESS, page_timeout=settings.PAGE_TIMEOUT
        )

        # Create progress callback for extraction phase
        def on_extraction_progress(current: int, total: int) -> None:
            # Calculate progress: scraping is 0-50%, extraction is 50-100%
            extraction_percentage = (current / total) * 50 if total else 0
            overall_progress = 50 + extraction_percentage

            tracker.update_progress(
                task_id,
                int(overall_progress),
                100,
                f"Extracting results: {current}/{total} rows processed...",
            )

        # Create progress callback for scraping phase
        def on_scraping_progress(step: int, total_steps: int, message: str) -> None:
            # Scraping phase is 0-50%
            scraping_percentage = (step / total_steps) * 50 if total_steps else 0

            tracker.update_progress(task_id, int(scraping_percentage), 100, message)

        tracker.update_progress(
            task_id, 5, 100, "Starting browser and navigating to PCSO website..."
        )

        result = scraper.scrape_lottery_data(
            game_type=game_type,
            start_date=start_date,
            end_date=end_date,
            save_path=data_path,
            progress_callback=on_extraction_progress,
            scraping_progress_callback=on_scraping_progress,
        )

        was_cached = result.get("cached", False)

        tracker.complete_task(
            task_id,
            f"{'Loaded' if was_cached else 'Scraped'} {result['total_draws']} draws successfully",
            result={
                "success": True,
                "filename": result["filename"],
                "total_draws": result["total_draws"],
                "cached": was_cached,
            },
        )

    except Exception as e:
        logger.error(f"Error in scraping thread: {str(e)}", exc_info=True)
        tracker.fail_task(task_id, "Scraping failed. Check server logs for details.")

    finally:
        semaphore.release()
