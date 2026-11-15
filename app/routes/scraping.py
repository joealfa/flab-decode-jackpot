"""Scraping HTTP routes."""

import logging
import threading
import uuid

from flask import Blueprint, jsonify, request

from app.exceptions import (  # noqa: E402
    BadRequestException,
    InternalServerException,
    ValidationException,
)
from app.services.jobs import scrape_data_thread
from app.validators import (  # noqa: E402
    parse_date,
    require_fields,
    require_json_body,
    validate_date_range,
    validate_game_type,
)
from app.web import (
    HTTPResponse,
    build_error_response,
    config,
    progress_tracker,
    scrape_semaphore,
)

logger = logging.getLogger(__name__)
blueprint = Blueprint("scraping", __name__)


@blueprint.route("/scrape", methods=["POST"])
def scrape_data() -> HTTPResponse:
    """
    Endpoint to trigger data scraping.
    Expects JSON with: game_type, start_date, end_date
    Returns task_id for progress tracking
    """
    logger.info("Received scrape request")

    try:
        data = require_json_body(request.get_json())
        logger.info(f"Request data: {data}")

        require_fields(data, ["game_type", "start_date", "end_date"])
        game_type = validate_game_type(data["game_type"])
        start_date = parse_date(data["start_date"], "start_date")
        end_date = parse_date(data["end_date"], "end_date")
        validate_date_range(start_date, end_date)

        logger.info(f"Parsed dates - Start: {start_date}, End: {end_date}")

        task_id = str(uuid.uuid4())

        if not scrape_semaphore.acquire(blocking=False):
            return jsonify(
                {"success": False, "error": "A scraping task is already running"}
            ), 429

        try:
            # Also clean here so leftovers are removed even without the scheduler.
            progress_tracker.cleanup_all()
        except Exception:
            logger.warning("Progress cleanup before scrape failed", exc_info=True)

        try:
            progress_tracker.create_task(task_id)
            thread = threading.Thread(
                target=scrape_data_thread,
                args=(
                    task_id,
                    game_type,
                    start_date,
                    end_date,
                    config.DATA_PATH,
                    progress_tracker._get_current_object(),
                    scrape_semaphore._get_current_object(),
                    config._get_current_object(),
                ),
                daemon=True,
            )
            thread.start()
        except Exception:
            scrape_semaphore.release()
            raise

        logger.info(f"Started scraping task {task_id} for {game_type}")
        return jsonify(
            {"success": True, "task_id": task_id, "message": "Scraping started"}
        )

    except (ValidationException, BadRequestException) as e:
        logger.warning(f"Validation error: {str(e)}")
        return build_error_response(e, 400)
    except Exception as e:
        logger.error(f"Unexpected error during scraping: {str(e)}", exc_info=True)
        error = InternalServerException("An unexpected error occurred", details={})
        return build_error_response(error, 500)


@blueprint.route("/api/progress/<task_id>")
def get_progress(task_id: str) -> HTTPResponse:
    """Get progress for a scraping task."""
    try:
        try:
            task_id = str(uuid.UUID(task_id))
        except ValueError:
            return jsonify({"success": False, "error": "Task not found"}), 404

        progress = progress_tracker.get_progress(task_id)

        if not progress:
            return jsonify({"success": False, "error": "Task not found"}), 404

        return jsonify({"success": True, "progress": progress})
    except Exception as e:
        # Log the error but don't crash - return a temporary error response
        logger.error(f"Error getting progress for task {task_id}: {str(e)}")
        return jsonify(
            {
                "success": False,
                "error": "Temporary error reading progress. Please try again.",
                "retry": True,
            }
        ), 500
