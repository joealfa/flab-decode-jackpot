"""
Fortune Lab: Decoding the Jackpot
Main Flask Application
"""

import os
import json
import logging
import uuid
import threading
import time
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
import numpy as np
from datetime import datetime
from typing import Any, Dict, Optional
from flask import Flask, render_template, request, jsonify, make_response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# Load environment variables BEFORE importing app modules that read config
load_dotenv()

from app.config import config  # noqa: E402
from app.exceptions import (  # noqa: E402
    ValidationException,
    DataNotFoundException,
    BadRequestException,
    InternalServerException,
)
from app.validators import (  # noqa: E402
    require_json_body,
    require_fields,
    validate_game_type,
    parse_date,
    validate_date_range,
    validate_lottery_numbers,
    validate_cleanup_strategy,
    game_type_to_slug,
)
from app.modules.scraper import PCSOScraper  # noqa: E402
from app.modules.analyzer import LotteryAnalyzer  # noqa: E402
from app.modules.progress_tracker import ProgressTracker  # noqa: E402
from app.modules.accuracy_analyzer import AccuracyAnalyzer  # noqa: E402
from app.modules.ai_analyzer import AIAnalyzer  # noqa: E402

# Configure logging (console only)
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Suppress noisy third-party loggers
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger.info("=" * 60)
logger.info("Fortune Lab Application Starting")
logger.info(f"Configuration loaded: DEBUG={config.DEBUG}, LOG_LEVEL={config.LOG_LEVEL}")
logger.info("=" * 60)


app = Flask(__name__, template_folder="app/templates", static_folder="app/static")

# Apply configuration from centralized config
app.config.update(config.flask_config)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[config.RATE_LIMIT_GENERAL],
    enabled=config.RATE_LIMIT_ENABLED,
    storage_uri="memory://",
)

# Initialize progress tracker
progress_tracker = ProgressTracker(progress_dir=config.PROGRESS_PATH)

# Initialize background scheduler for periodic cleanup
scheduler = BackgroundScheduler()
scheduler.start()


# Scheduled cleanup job - runs every 5 minutes
def scheduled_progress_cleanup():
    """Background task to clean up old progress files."""
    try:
        results = progress_tracker.cleanup_all()
        if results["total_cleaned"] > 0:
            logger.info(
                f"Scheduled cleanup: {results['total_cleaned']} files removed "
                f"(completed: {results['completed_cleaned']}, "
                f"stale: {results['stale_cleaned']}, "
                f"old: {results['old_cleaned']})"
            )
    except Exception as e:
        logger.error(f"Error in scheduled cleanup: {str(e)}", exc_info=True)


# Add job to run every 5 minutes
scheduler.add_job(
    func=scheduled_progress_cleanup,
    trigger="interval",
    minutes=5,
    id="progress_cleanup",
    name="Clean up old progress files",
    replace_existing=True,
)

# Shutdown scheduler when app exits
atexit.register(lambda: scheduler.shutdown())


def convert_to_serializable(obj):
    """Convert NumPy types to native Python types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_to_serializable(item) for item in obj)
    else:
        return obj


def build_error_response(exception: Exception, default_status: int = 400):
    """Create a consistent JSON error response from an exception instance."""
    status_code = default_status
    payload: Dict[str, Any]

    to_response = getattr(exception, "to_response_dict", None)
    if callable(to_response):
        response_data = to_response()
        if isinstance(response_data, tuple) and len(response_data) == 2:
            payload, status_code = response_data
        else:
            payload = response_data  # type: ignore[assignment]
    else:
        payload = {
            "success": False,
            "error": str(exception),
        }

    if not isinstance(payload, dict):
        payload = {"success": False, "error": str(exception)}

    payload.setdefault("success", False)

    details = getattr(exception, "details", None)
    if details and "details" not in payload:
        payload["details"] = details

    return jsonify(payload), status_code


def validate_filename(filename: str, allowed_dir: str) -> str:
    """Validate a filename to prevent path traversal attacks.

    Args:
        filename: The user-supplied filename to validate.
        allowed_dir: The directory the file must reside in.

    Returns:
        The safe, resolved file path.

    Raises:
        BadRequestException: If the filename contains path traversal sequences.
    """
    if not filename:
        raise BadRequestException("Filename is required")

    # Strip any path components - only allow the base filename
    safe_name = os.path.basename(filename)
    if safe_name != filename:
        raise BadRequestException(
            "Invalid filename",
            details={"reason": "Filename must not contain path separators"},
        )

    filepath = os.path.realpath(os.path.join(allowed_dir, safe_name))
    allowed_real = os.path.realpath(allowed_dir)

    if not filepath.startswith(allowed_real + os.sep) and filepath != allowed_real:
        raise BadRequestException(
            "Invalid filename", details={"reason": "Path traversal detected"}
        )

    return filepath


@app.after_request
def set_security_headers(response):
    """Add security headers to all responses."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if not config.DEBUG:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


def select_analysis_snapshot(
    game_slug: str, analysis_dir: str, draw_date: datetime
) -> Optional[Dict[str, Any]]:
    """Select the most relevant analysis snapshot for a given draw date.

    Prefers analyses generated on or before the draw date and whose coverage
    does not extend beyond the draw itself. Falls back gracefully to the closest
    available snapshot when a perfect pre-draw match is unavailable.

    Args:
        game_slug: Normalized game identifier (e.g., "Grand_Lotto_6-55").
        analysis_dir: Directory path containing analysis JSON files.
        draw_date: Draw date as a datetime instance.

    Returns:
        Dictionary containing metadata and loaded analysis data, or None if no
        candidate snapshot is available.
    """
    if not os.path.exists(analysis_dir):
        return None

    draw_day = draw_date.date()
    draw_cutoff = datetime.combine(draw_day, datetime.max.time())

    best_pre_with_coverage: Optional[Dict[str, Any]] = None
    best_pre: Optional[Dict[str, Any]] = None
    best_future: Optional[Dict[str, Any]] = None
    fallback_latest: Optional[Dict[str, Any]] = None

    for filename in os.listdir(analysis_dir):
        if not filename.startswith(
            f"analysis_result_{game_slug}_"
        ) or not filename.endswith(".json"):
            continue

        filepath = os.path.join(analysis_dir, filename)

        try:
            with open(filepath, "r", encoding="utf-8") as analysis_file:
                analysis_data = json.load(analysis_file)
        except Exception as exc:  # Defensive: skip unreadable files
            logger.error(
                "Failed to read analysis snapshot %s: %s",
                filename,
                str(exc),
                exc_info=True,
            )
            continue

        analyzed_at_raw = analysis_data.get("analyzed_at")
        analyzed_at: Optional[datetime] = None
        if analyzed_at_raw:
            try:
                analyzed_at = datetime.strptime(analyzed_at_raw, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                logger.warning(
                    "Invalid analyzed_at format in %s: %s", filename, analyzed_at_raw
                )

        coverage_end_raw = analysis_data.get("date_range", {}).get("end")
        coverage_end = None
        if coverage_end_raw:
            try:
                coverage_end = datetime.strptime(coverage_end_raw, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(
                    "Invalid coverage end date in %s: %s", filename, coverage_end_raw
                )

        candidate = {
            "filename": filename,
            "filepath": filepath,
            "analysis_data": analysis_data,
            "analyzed_at": analyzed_at,
            "coverage_end": coverage_end,
        }

        # Track latest by filesystem timestamp as a final fallback
        if fallback_latest is None:
            fallback_latest = candidate
        else:
            try:
                if os.path.getmtime(filepath) > os.path.getmtime(
                    fallback_latest["filepath"]
                ):
                    fallback_latest = candidate
            except OSError:
                fallback_latest = candidate

        if analyzed_at is None:
            continue

        if analyzed_at <= draw_cutoff:
            # Candidate generated before (or on) the draw date
            if coverage_end and coverage_end <= draw_day:
                if (
                    best_pre_with_coverage is None
                    or analyzed_at > best_pre_with_coverage["analyzed_at"]
                ):
                    best_pre_with_coverage = candidate
            else:
                if best_pre is None or analyzed_at > best_pre["analyzed_at"]:
                    best_pre = candidate
        else:
            if best_future is None or analyzed_at < best_future["analyzed_at"]:
                best_future = candidate

    if best_pre_with_coverage:
        best_pre_with_coverage["selection_reason"] = "pre_draw_with_coverage"
        return best_pre_with_coverage
    if best_pre:
        best_pre["selection_reason"] = "pre_draw"
        return best_pre
    if best_future:
        best_future["selection_reason"] = "post_draw_nearest"
        return best_future
    if fallback_latest:
        fallback_latest["selection_reason"] = "filesystem_latest"
        return fallback_latest
    return None


@app.route("/test-chart")
def test_chart():
    """Test page to verify Chart.js is working"""
    return render_template("test_chart.html")


@app.route("/")
def index():
    """Main dashboard page."""
    # Get list of available result files with metadata
    data_path = config.DATA_PATH
    result_files = []

    if os.path.exists(data_path):
        for filename in os.listdir(data_path):
            if filename.endswith(".json") and filename.startswith("result_"):
                # Parse filename: result_GameType_Date.json
                # Example: result_Super_Lotto_6-49_20251018.json
                parts = filename.replace("result_", "").replace(".json", "")

                # Split to get game type and date
                parts_list = parts.split("_")
                if len(parts_list) >= 2:
                    # Last part is the date
                    date_str = parts_list[-1]
                    # Everything else is game type
                    game_type_parts = parts_list[:-1]
                    game_type_raw = "_".join(game_type_parts)

                    # Format game type (replace underscores with spaces, keep dashes for number format)
                    game_type = game_type_raw.replace("_", " ").replace("-", "/")

                    # Format date from YYYYMMDD to YYYY-MM-DD
                    try:
                        if len(date_str) == 8:
                            year = date_str[:4]
                            month = date_str[4:6]
                            day = date_str[6:8]
                            formatted_date = f"{year}-{month}-{day}"
                        else:
                            formatted_date = date_str
                    except ValueError, IndexError, TypeError:
                        formatted_date = date_str

                    result_files.append(
                        {
                            "filename": filename,
                            "game_type": game_type,
                            "date": formatted_date,
                            "mtime": os.path.getmtime(
                                os.path.join(data_path, filename)
                            ),
                        }
                    )

    # Sort by modification time (newest first)
    result_files.sort(key=lambda x: x["mtime"], reverse=True)

    return render_template("index.html", result_files=result_files)


def scrape_data_thread(task_id, game_type, start_date, end_date, data_path):
    """Background thread for scraping data."""
    try:
        progress_tracker.create_task(task_id)
        progress_tracker.update_progress(task_id, 0, 100, "Initializing scraper...")

        scraper = PCSOScraper(headless=config.HEADLESS)

        # Create progress callback for extraction phase
        def on_extraction_progress(current, total):
            # Calculate progress: scraping is 0-50%, extraction is 50-100%
            extraction_percentage = (current / total) * 50  # 50% of total progress
            overall_progress = 50 + extraction_percentage

            progress_tracker.update_progress(
                task_id,
                int(overall_progress),
                100,
                f"Extracting results: {current}/{total} rows processed...",
            )

        # Create progress callback for scraping phase
        def on_scraping_progress(step, total_steps, message):
            # Scraping phase is 0-50%
            scraping_percentage = (step / total_steps) * 50

            progress_tracker.update_progress(
                task_id, int(scraping_percentage), 100, message
            )

        progress_tracker.update_progress(
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

        progress_tracker.complete_task(
            task_id,
            f"{'Loaded' if was_cached else 'Scraped'} {result['total_draws']} draws successfully",
        )

        # Store result in progress data for retrieval
        progress_file = os.path.join(progress_tracker.progress_dir, f"{task_id}.json")
        with open(progress_file, "r") as f:
            data = json.load(f)

        data["result"] = {
            "success": True,
            "filename": result["filename"],
            "total_draws": result["total_draws"],
            "cached": was_cached,
        }

        with open(progress_file, "w") as f:
            json.dump(data, f)

        # Schedule cleanup of this completed task after 3 minutes
        def delayed_cleanup():
            time.sleep(180)  # Wait 3 minutes
            try:
                progress_tracker.cleanup_task(task_id)
                logger.info(f"Cleaned up completed task {task_id}")
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up task {task_id}: {str(cleanup_error)}")

        threading.Thread(target=delayed_cleanup, daemon=True).start()

    except Exception as e:
        logger.error(f"Error in scraping thread: {str(e)}", exc_info=True)
        progress_tracker.fail_task(task_id, str(e))

        # Schedule cleanup of this failed task after 5 minutes
        def delayed_cleanup():
            time.sleep(300)  # Wait 5 minutes
            try:
                progress_tracker.cleanup_task(task_id)
                logger.info(f"Cleaned up failed task {task_id}")
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up task {task_id}: {str(cleanup_error)}")

        threading.Thread(target=delayed_cleanup, daemon=True).start()


@app.route("/scrape", methods=["POST"])
@limiter.limit(config.RATE_LIMIT_SCRAPE)
def scrape_data():
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

        # Generate unique task ID
        task_id = str(uuid.uuid4())

        # Start scraping in background thread
        thread = threading.Thread(
            target=scrape_data_thread,
            args=(task_id, game_type, start_date, end_date, config.DATA_PATH),
        )
        thread.daemon = True
        thread.start()

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


@app.route("/api/progress/<task_id>")
def get_progress(task_id):
    """Get progress for a scraping task."""
    try:
        progress = progress_tracker.get_progress(task_id)

        if not progress:
            return jsonify({"success": False, "error": "Task not found"}), 404

        # Cleanup is handled by the scheduled background job (every 5 minutes)
        # No need to spawn a thread on every progress check

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


@app.route("/analyze/<filename>")
def analyze(filename):
    """
    Run analysis and save report, then display dashboard.
    """
    try:
        # Load lottery data
        filepath = validate_filename(filename, config.DATA_PATH)

        if not os.path.exists(filepath):
            return "Result file not found", 404

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Create analyzer
        logger.info(f"Starting analysis for {filename}")
        analyzer = LotteryAnalyzer(data)

        # Get all analysis data
        overall_stats = analyzer.get_overall_statistics()
        day_analysis = analyzer.get_all_days_analysis()
        top_predictions = analyzer.generate_top_predictions(top_n=5)
        winning_predictions = analyzer.generate_winning_predictions(top_n=5)
        pattern_predictions = analyzer.generate_pattern_based_prediction(top_n=5)
        pattern_analysis = analyzer.analyze_consecutive_draw_patterns()

        # New comprehensive analyses
        temporal_patterns = analyzer.analyze_temporal_patterns()
        historical_observations = analyzer.get_historical_observations()
        ultimate_predictions = analyzer.generate_ultimate_predictions(top_n=5)

        chart_data = analyzer.get_chart_data()

        # Save analysis report
        analysis_report = {
            "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source_file": filename,
            "game_type": data["game_type"],
            "date_range": {"start": data["start_date"], "end": data["end_date"]},
            "total_draws": data["total_draws"],
            "overall_stats": overall_stats,
            "day_analysis": day_analysis,
            "top_predictions": top_predictions,
            "winning_predictions": winning_predictions,
            "pattern_predictions": pattern_predictions,
            "pattern_analysis": pattern_analysis,
            "temporal_patterns": temporal_patterns,
            "historical_observations": historical_observations,
            "ultimate_predictions": ultimate_predictions,
            "chart_data": chart_data,
        }

        # Convert all NumPy types to native Python types
        analysis_report = convert_to_serializable(analysis_report)

        # Save report to analysis directory
        analysis_dir = config.ANALYSIS_PATH
        os.makedirs(analysis_dir, exist_ok=True)

        # Create report filename with timestamp
        base_name = filename.replace(".json", "")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"analysis_{base_name}_{timestamp}.json"
        report_path = os.path.join(analysis_dir, report_filename)

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(analysis_report, f, indent=2, ensure_ascii=False)

        logger.info(f"Analysis report saved: {report_filename}")

        return render_template(
            "dashboard.html",
            data=data,
            overall_stats=overall_stats,
            day_analysis=day_analysis,
            top_predictions=top_predictions,
            winning_predictions=winning_predictions,
            pattern_predictions=pattern_predictions,
            pattern_analysis=pattern_analysis,
            temporal_patterns=temporal_patterns,
            historical_observations=historical_observations,
            ultimate_predictions=ultimate_predictions,
            chart_data=chart_data,
            filename=filename,
            report_filename=report_filename,
        )

    except BadRequestException as e:
        return build_error_response(e, 400)
    except Exception as e:
        logger.error(f"Error analyzing data: {str(e)}", exc_info=True)
        error = InternalServerException("Analysis failed")
        return build_error_response(error, 500)


@app.route("/api/analyze", methods=["POST"])
@limiter.limit(config.RATE_LIMIT_ANALYZE)
def api_analyze():
    """
    API endpoint to analyze a specific result file.
    Returns JSON with analysis data.
    """
    try:
        data = request.get_json()
        filename = data.get("filename")

        if not filename:
            raise BadRequestException("Filename is required")

        # Load data
        filepath = validate_filename(filename, config.DATA_PATH)

        if not os.path.exists(filepath):
            raise DataNotFoundException(filename)

        with open(filepath, "r", encoding="utf-8") as f:
            lottery_data = json.load(f)

        # Create analyzer
        analyzer = LotteryAnalyzer(lottery_data)

        # Get analysis
        overall_stats = analyzer.get_overall_statistics()
        day_analysis = analyzer.get_all_days_analysis()
        top_predictions = analyzer.generate_top_predictions(top_n=5)
        winning_predictions = analyzer.generate_winning_predictions(top_n=5)
        chart_data = analyzer.get_chart_data()

        return jsonify(
            {
                "success": True,
                "data": lottery_data,
                "overall_stats": overall_stats,
                "day_analysis": day_analysis,
                "top_predictions": top_predictions,
                "winning_predictions": winning_predictions,
                "chart_data": chart_data,
            }
        )

    except DataNotFoundException as e:
        logger.warning(f"Data not found: {str(e)}")
        return build_error_response(e, 404)
    except BadRequestException as e:
        logger.warning(f"Bad request: {str(e)}")
        return build_error_response(e, 400)
    except Exception as e:
        logger.error(f"Error in API analyze: {str(e)}", exc_info=True)
        error = InternalServerException("Analysis failed", details={})
        return build_error_response(error, 500)


@app.route("/api/ai-analyze", methods=["POST"])
@limiter.limit(config.RATE_LIMIT_ANALYZE)
def api_ai_analyze():
    """
    API endpoint for AI-powered analysis.
    Takes an analysis filename and returns AI interpretation.
    """
    try:
        # Check if AI is enabled
        if not config.OLLAMA_ENABLED:
            raise BadRequestException(
                "AI analysis is not enabled. Set OLLAMA_ENABLED=True in configuration."
            )

        data = request.get_json()
        analysis_filename = data.get("filename")

        if not analysis_filename:
            raise BadRequestException("Analysis filename is required")

        # Determine if it's a result or analysis file
        if analysis_filename.startswith("analysis_"):
            # It's already an analysis file
            analysis_path = os.path.join(config.ANALYSIS_PATH, analysis_filename)
        else:
            # It's a result file, find the latest analysis
            # Try to find corresponding analysis file
            base_name = analysis_filename.replace(".json", "")
            analysis_files = []

            if os.path.exists(config.ANALYSIS_PATH):
                for f in os.listdir(config.ANALYSIS_PATH):
                    if f.startswith(f"analysis_{base_name}_") and f.endswith(".json"):
                        analysis_files.append(f)

            if not analysis_files:
                raise DataNotFoundException(
                    f"No analysis found for {analysis_filename}. Please generate analysis first."
                )

            # Get the most recent analysis file
            analysis_files.sort(reverse=True)
            analysis_path = os.path.join(config.ANALYSIS_PATH, analysis_files[0])

        # Load analysis data
        if not os.path.exists(analysis_path):
            raise DataNotFoundException(f"Analysis file not found: {analysis_filename}")

        logger.info(f"Loading analysis for AI: {analysis_path}")

        with open(analysis_path, "r", encoding="utf-8") as f:
            analysis_data = json.load(f)

        # Initialize AI analyzer
        ai_analyzer = AIAnalyzer()

        # Check Ollama status first
        status = ai_analyzer.check_ollama_status()
        if not status.get("running"):
            raise InternalServerException(
                "Ollama is not running. Please start Ollama service.",
                details={"error": status.get("error", "Unknown error")},
            )

        if not status.get("model_available"):
            raise InternalServerException(
                f"Model '{ai_analyzer.model}' is not available.",
                details={
                    "available_models": status.get("available_models", []),
                    "configured_model": ai_analyzer.model,
                },
            )

        # Perform AI analysis
        logger.info(f"Starting AI analysis for {analysis_filename}")
        ai_result = ai_analyzer.analyze_lottery_report(analysis_data)

        logger.info("AI analysis completed successfully")

        return jsonify(ai_result)

    except BadRequestException as e:
        logger.warning(f"Bad request in AI analyze: {str(e)}")
        return build_error_response(e, 400)
    except DataNotFoundException as e:
        logger.warning(f"Data not found in AI analyze: {str(e)}")
        return build_error_response(e, 404)
    except InternalServerException as e:
        logger.error(f"Internal error in AI analyze: {str(e)}")
        return build_error_response(e, 500)
    except Exception as e:
        logger.error(f"Unexpected error in AI analyze: {str(e)}", exc_info=True)
        error = InternalServerException("AI analysis failed", details={"error": str(e)})
        return build_error_response(error, 500)


@app.route("/api/ollama-status", methods=["GET"])
def api_ollama_status():
    """Check Ollama service status."""
    try:
        ai_analyzer = AIAnalyzer()
        status = ai_analyzer.check_ollama_status()
        return jsonify({"success": True, "status": status})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/files")
def api_list_files():
    """API endpoint to list all result files."""
    try:
        data_path = config.DATA_PATH
        result_files = []

        if os.path.exists(data_path):
            for filename in os.listdir(data_path):
                if filename.endswith(".json"):
                    filepath = os.path.join(data_path, filename)

                    # Get file metadata
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    result_files.append(
                        {
                            "filename": filename,
                            "game_type": data.get("game_type"),
                            "total_draws": data.get("total_draws"),
                            "date_range": data.get("start_date")
                            + " to "
                            + data.get("end_date"),
                            "scraped_at": data.get("scraped_at"),
                        }
                    )

        return jsonify({"success": True, "files": result_files})

    except Exception as e:
        logger.error(f"Error listing files: {str(e)}", exc_info=True)
        error = InternalServerException("Failed to list files", details={})
        return jsonify(error.to_response_dict())


@app.route("/api/analysis-history/<filename>")
def get_analysis_history(filename):
    """Get all analysis reports for a specific result file."""
    try:
        analysis_dir = config.ANALYSIS_PATH

        if not os.path.exists(analysis_dir):
            return jsonify({"success": True, "reports": []})

        # Find all analysis reports for this file
        base_name = filename.replace(".json", "")

        reports = []
        for report_file in os.listdir(analysis_dir):
            if report_file.startswith(
                f"analysis_{base_name}_"
            ) and report_file.endswith(".json"):
                report_path = os.path.join(analysis_dir, report_file)

                # Get file metadata
                file_stat = os.stat(report_path)

                # Load report to get analyzed_at timestamp
                with open(report_path, "r", encoding="utf-8") as f:
                    report_data = json.load(f)

                reports.append(
                    {
                        "filename": report_file,
                        "analyzed_at": report_data.get("analyzed_at"),
                        "created_at": datetime.fromtimestamp(
                            file_stat.st_ctime
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                        "size": file_stat.st_size,
                    }
                )

        # Sort by analyzed_at (most recent first)
        reports.sort(key=lambda x: x["analyzed_at"], reverse=True)

        return jsonify({"success": True, "reports": reports, "count": len(reports)})

    except Exception as e:
        logger.error(f"Error getting analysis history: {str(e)}", exc_info=True)
        error = InternalServerException("Failed to get analysis history", details={})
        return jsonify(error.to_response_dict())


@app.route("/view-report/<report_filename>")
def view_report(report_filename):
    """View a specific analysis report."""
    try:
        report_path = validate_filename(report_filename, config.ANALYSIS_PATH)

        if not os.path.exists(report_path):
            return "Analysis report not found", 404

        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        # Load the original data file for context
        source_file = report.get("source_file")
        data_path = os.path.join(config.DATA_PATH, source_file)

        data = {}
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        return render_template(
            "dashboard.html",
            data=data if data else report,
            overall_stats=report["overall_stats"],
            day_analysis=report["day_analysis"],
            top_predictions=report["top_predictions"],
            winning_predictions=report["winning_predictions"],
            pattern_predictions=report.get("pattern_predictions", []),
            pattern_analysis=report.get("pattern_analysis", {}),
            temporal_patterns=report.get("temporal_patterns", {}),
            historical_observations=report.get("historical_observations", {}),
            ultimate_predictions=report.get("ultimate_predictions", []),
            chart_data=report["chart_data"],
            filename=source_file,
            report_filename=report_filename,
            analyzed_at=report["analyzed_at"],
            is_historical=True,
        )

    except BadRequestException as e:
        return build_error_response(e, 400)
    except Exception as e:
        logger.error(f"Error viewing report: {str(e)}", exc_info=True)
        error = InternalServerException("Failed to load report")
        return build_error_response(error, 500)


@app.route("/api/result-files")
def get_result_files_for_game():
    """Get all result files for a specific game type."""
    try:
        game_type = request.args.get("game_type")

        if not game_type:
            raise BadRequestException("game_type parameter is required")

        validate_game_type(game_type)

        data_path = config.DATA_PATH
        result_files = []
        game_slug = game_type_to_slug(game_type)

        if os.path.exists(data_path):
            for filename in os.listdir(data_path):
                if filename.startswith(f"result_{game_slug}_") and filename.endswith(
                    ".json"
                ):
                    filepath = os.path.join(data_path, filename)

                    # Get file metadata
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    result_files.append(
                        {
                            "filename": filename,
                            "display_name": f"{data.get('game_type')} - {data.get('start_date')} to {data.get('end_date')} ({data.get('total_draws')} draws)",
                            "end_date": data.get("end_date"),
                            "total_draws": data.get("total_draws"),
                            "scraped_at": data.get("scraped_at"),
                        }
                    )

        # Sort by end date (most recent first)
        result_files.sort(key=lambda x: x["end_date"], reverse=True)

        return jsonify({"success": True, "files": result_files})

    except (ValidationException, BadRequestException) as e:
        logger.warning(f"Validation error: {str(e)}")
        return build_error_response(e, 400)
    except Exception as e:
        logger.error(f"Error getting result files: {str(e)}", exc_info=True)
        error = InternalServerException("Failed to list result files", details={})
        return build_error_response(error, 500)


@app.route("/api/submit-actual-result", methods=["POST"])
def submit_actual_result():
    """Submit actual draw result for accuracy comparison and add to dataset."""
    try:
        data = require_json_body(request.get_json())

        require_fields(data, ["game_type", "draw_date", "numbers"])
        game_type = validate_game_type(data["game_type"])
        draw_date = parse_date(data["draw_date"], "draw_date")
        actual_numbers = validate_lottery_numbers(data["numbers"], game_type)

        jackpot = data.get("jackpot", "N/A")
        winners = data.get("winners", "N/A")
        target_filename = data.get("target_filename")
        draw_date_str = data["draw_date"]

        # Find result files for this game type
        data_path = config.DATA_PATH
        result_files = []
        game_slug = game_type_to_slug(game_type)

        for filename in os.listdir(data_path):
            if filename.startswith(f"result_{game_slug}_") and filename.endswith(
                ".json"
            ):
                filepath = os.path.join(data_path, filename)
                mtime = os.path.getmtime(filepath)
                result_files.append((filename, filepath, mtime))

        if not result_files:
            return jsonify(
                {"success": False, "error": f"No result files found for {game_type}"}
            ), 404

        # Determine which file to update
        if target_filename:
            # User specified a specific file
            target_file = os.path.join(data_path, target_filename)
            if not os.path.exists(target_file):
                return jsonify(
                    {
                        "success": False,
                        "error": f"Target file {target_filename} not found",
                    }
                ), 404
            result_file_path = target_file
            logger.info(f"Using user-selected file: {target_filename}")
        else:
            # Use the latest result file (default behavior)
            result_files.sort(key=lambda x: x[2], reverse=True)
            result_file_path = result_files[0][1]
            logger.info(f"Using latest file: {result_files[0][0]}")

        # Load the result file
        with open(result_file_path, "r", encoding="utf-8") as f:
            result_data = json.load(f)

        # Create new draw entry
        new_draw = {
            "game": game_type,
            "date": draw_date.strftime("%m/%d/%Y"),
            "day_of_week": draw_date.strftime("%A"),
            "numbers": actual_numbers,
            "jackpot": jackpot,
            "winners": winners,
        }

        # Check if this draw already exists
        existing_draw = None
        for idx, draw in enumerate(result_data["results"]):
            if draw["date"] == new_draw["date"]:
                existing_draw = idx
                break

        if existing_draw is not None:
            # Update existing draw
            result_data["results"][existing_draw] = new_draw
            logger.info(f"Updated existing draw for {new_draw['date']}")
        else:
            # Add new draw (insert at the beginning for most recent)
            result_data["results"].insert(0, new_draw)
            result_data["total_draws"] = len(result_data["results"])
            logger.info(f"Added new draw for {new_draw['date']}")

        # Update end date if necessary
        result_data["end_date"] = max(
            result_data.get("end_date", draw_date.strftime("%Y-%m-%d")),
            draw_date.strftime("%Y-%m-%d"),
        )

        # Save updated result file
        with open(result_file_path, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)

        # Load the latest analysis report for comparison
        analysis_dir = config.ANALYSIS_PATH
        accuracy_results = None

        if os.path.exists(analysis_dir):
            snapshot = select_analysis_snapshot(game_slug, analysis_dir, draw_date)

            if snapshot:
                analysis_data = snapshot["analysis_data"]
                analysis_generated_at = snapshot.get("analyzed_at")
                coverage_end = snapshot.get("coverage_end")
                selection_reason = snapshot.get("selection_reason")

                logger.info(
                    "Using analysis snapshot %s (reason=%s) for draw %s",
                    snapshot["filename"],
                    selection_reason,
                    draw_date_str,
                )

                # Perform accuracy comparison
                accuracy_results = {
                    "actual_numbers": actual_numbers,
                    "draw_date": draw_date_str,
                    "game_type": game_type,
                    "top_predictions_comparison": [],
                    "winning_predictions_comparison": [],
                    "pattern_predictions_comparison": [],
                    "analysis_snapshot": {
                        "filename": snapshot["filename"],
                        "generated_at": analysis_generated_at.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        if analysis_generated_at
                        else analysis_data.get("analyzed_at"),
                        "coverage_end": coverage_end.strftime("%Y-%m-%d")
                        if coverage_end
                        else analysis_data.get("date_range", {}).get("end"),
                        "selection_reason": selection_reason,
                    },
                }

                # Check top predictions
                for idx, pred in enumerate(analysis_data.get("top_predictions", []), 1):
                    predicted_numbers = sorted(pred["numbers"])
                    matched_numbers = sorted(
                        set(actual_numbers) & set(predicted_numbers)
                    )
                    matches = len(matched_numbers)

                    accuracy_results["top_predictions_comparison"].append(
                        {
                            "rank": idx,
                            "predicted_numbers": predicted_numbers,
                            "matches": matches,
                            "matched_numbers": matched_numbers,
                            "confidence_score": pred.get("confidence_score", 0),
                        }
                    )

                # Check winning predictions
                for idx, pred in enumerate(
                    analysis_data.get("winning_predictions", []), 1
                ):
                    predicted_numbers = sorted(pred["numbers"])
                    matched_numbers = sorted(
                        set(actual_numbers) & set(predicted_numbers)
                    )
                    matches = len(matched_numbers)

                    accuracy_results["winning_predictions_comparison"].append(
                        {
                            "rank": idx,
                            "predicted_numbers": predicted_numbers,
                            "matches": matches,
                            "matched_numbers": matched_numbers,
                            "win_probability_score": pred.get(
                                "win_probability_score", 0
                            ),
                        }
                    )

                # Check pattern predictions
                for idx, pred in enumerate(
                    analysis_data.get("pattern_predictions", []), 1
                ):
                    predicted_numbers = sorted(pred["numbers"])
                    matched_numbers = sorted(
                        set(actual_numbers) & set(predicted_numbers)
                    )
                    matches = len(matched_numbers)

                    accuracy_results["pattern_predictions_comparison"].append(
                        {
                            "rank": idx,
                            "predicted_numbers": predicted_numbers,
                            "matches": matches,
                            "matched_numbers": matched_numbers,
                            "pattern_score": pred.get("pattern_score", 0),
                        }
                    )

                # Save accuracy results
                accuracy_dir = os.path.join(config.DATA_PATH, "accuracy")
                os.makedirs(accuracy_dir, exist_ok=True)

                # Remove outdated snapshots for the same draw to avoid confusion
                for existing_filename in os.listdir(accuracy_dir):
                    if not existing_filename.startswith(
                        f"accuracy_{game_slug}_"
                    ) or not existing_filename.endswith(".json"):
                        continue

                    existing_path = os.path.join(accuracy_dir, existing_filename)
                    try:
                        with open(
                            existing_path, "r", encoding="utf-8"
                        ) as existing_file:
                            existing_data = json.load(existing_file)
                    except Exception:
                        continue

                    if (
                        existing_data.get("game_type") == game_type
                        and existing_data.get("draw_date") == draw_date_str
                    ):
                        try:
                            os.remove(existing_path)
                            logger.info(
                                "Removed outdated accuracy snapshot %s",
                                existing_filename,
                            )
                        except OSError as exc:
                            logger.warning(
                                "Failed to remove outdated accuracy snapshot %s: %s",
                                existing_filename,
                                str(exc),
                            )

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                accuracy_filename = f"accuracy_{game_slug}_{timestamp}.json"
                accuracy_filepath = os.path.join(accuracy_dir, accuracy_filename)

                with open(accuracy_filepath, "w", encoding="utf-8") as f:
                    json.dump(accuracy_results, f, indent=2, ensure_ascii=False)
            else:
                logger.warning(
                    "No suitable analysis snapshot found for %s on %s",
                    game_type,
                    draw_date_str,
                )

        return jsonify(
            {
                "success": True,
                "message": f"Actual result {'updated' if existing_draw is not None else 'added'} successfully",
                "accuracy_results": accuracy_results,
                "result_file": os.path.basename(result_file_path),
                "total_draws": result_data["total_draws"],
            }
        )

    except DataNotFoundException as e:
        logger.warning(f"Data not found: {str(e)}")
        return build_error_response(e, 404)
    except (ValidationException, BadRequestException) as e:
        logger.warning(f"Validation error: {str(e)}")
        return build_error_response(e, 400)
    except Exception as e:
        logger.error(f"Error submitting actual result: {str(e)}", exc_info=True)
        error = InternalServerException("Failed to submit actual result", details={})
        return build_error_response(error, 500)


@app.route("/api/delete-report/<report_filename>", methods=["DELETE"])
def delete_report(report_filename):
    """Delete an analysis report."""
    try:
        report_path = validate_filename(report_filename, config.ANALYSIS_PATH)

        if not os.path.exists(report_path):
            raise DataNotFoundException(report_filename)

        # Delete the file
        os.remove(report_path)
        logger.info(f"Deleted analysis report: {report_filename}")

        return jsonify({"success": True, "message": "Report deleted successfully"})

    except DataNotFoundException as e:
        logger.warning(f"Report not found: {str(e)}")
        return build_error_response(e, 404)
    except Exception as e:
        logger.error(f"Error deleting report: {str(e)}", exc_info=True)
        error = InternalServerException("Failed to delete report", details={})
        return build_error_response(error, 500)


@app.route("/api/export-analysis/<report_filename>")
def export_analysis(report_filename):
    """Export analysis report as downloadable JSON."""
    try:
        report_path = validate_filename(report_filename, config.ANALYSIS_PATH)

        if not os.path.exists(report_path):
            raise DataNotFoundException(report_filename)

        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        # Create a response with proper headers for download
        response = make_response(json.dumps(report, indent=2, ensure_ascii=False))
        response.headers["Content-Type"] = "application/json"
        response.headers["Content-Disposition"] = (
            f"attachment; filename={report_filename}"
        )

        return response

    except DataNotFoundException as e:
        logger.warning(f"Report not found: {str(e)}")
        return build_error_response(e, 404)
    except Exception as e:
        logger.error(f"Error exporting analysis: {str(e)}", exc_info=True)
        error = InternalServerException("Failed to export analysis", details={})
        return build_error_response(error, 500)


@app.route("/api/cleanup-progress", methods=["POST"])
def cleanup_progress():
    """Manually cleanup old progress files with detailed results."""
    try:
        # Accept both JSON and no body (for simple curl requests)
        data = request.get_json(silent=True) or {}

        # Support different cleanup strategies
        strategy = validate_cleanup_strategy(data.get("strategy", "all"))

        if strategy == "all":
            # Comprehensive cleanup
            results = progress_tracker.cleanup_all()
            message = (
                f"Cleaned up {results['total_cleaned']} progress file(s): "
                f"{results['completed_cleaned']} completed, "
                f"{results['stale_cleaned']} stale, "
                f"{results['old_cleaned']} old"
            )
        elif strategy == "completed":
            max_age = data.get("max_age_seconds", 180)  # 3 minutes default
            cleaned = progress_tracker.cleanup_completed_tasks(max_age)
            results = {"completed_cleaned": cleaned, "total_cleaned": cleaned}
            message = f"Cleaned up {cleaned} completed progress file(s)"
        elif strategy == "stale":
            max_age = data.get("max_age_seconds", 600)  # 10 minutes default
            cleaned = progress_tracker.cleanup_stale_tasks(max_age)
            results = {"stale_cleaned": cleaned, "total_cleaned": cleaned}
            message = f"Cleaned up {cleaned} stale progress file(s)"
        elif strategy == "old":
            max_age_hours = data.get("max_age_hours", 24)
            cleaned = progress_tracker.cleanup_all_old_tasks(max_age_hours)
            results = {"old_cleaned": cleaned, "total_cleaned": cleaned}
            message = f"Cleaned up {cleaned} old progress file(s)"

        return jsonify({"success": True, "results": results, "message": message})

    except BadRequestException as e:
        logger.warning(f"Bad cleanup request: {str(e)}")
        return build_error_response(e, 400)
    except Exception as e:
        logger.error(f"Error cleaning up progress files: {str(e)}", exc_info=True)
        error = InternalServerException("Failed to cleanup progress files", details={})
        return build_error_response(error, 500)


@app.route("/api/accuracy-analysis", methods=["GET"])
def get_accuracy_analysis():
    """
    Get comprehensive accuracy analysis.

    Query Parameters:
        game_type: Optional game type filter (e.g., "Lotto 6/42")

    Returns:
        JSON with complete accuracy analysis
    """
    try:
        game_type = request.args.get("game_type")

        analyzer = AccuracyAnalyzer()
        analysis = analyzer.analyze_overall_accuracy(game_type)

        return jsonify({"success": True, "data": analysis})

    except DataNotFoundException as e:
        logger.warning(f"No accuracy data found: {str(e)}")
        return build_error_response(e, 404)
    except Exception as e:
        logger.error(f"Error analyzing accuracy: {str(e)}", exc_info=True)
        error = InternalServerException("Failed to analyze accuracy", details={})
        return build_error_response(error, 500)


@app.route("/api/accuracy-summary", methods=["GET"])
def get_accuracy_summary():
    """
    Get quick accuracy summary.

    Query Parameters:
        game_type: Optional game type filter

    Returns:
        JSON with summary metrics
    """
    try:
        game_type = request.args.get("game_type")

        analyzer = AccuracyAnalyzer()
        summary = analyzer.get_accuracy_summary(game_type)

        return jsonify({"success": True, "data": summary})

    except DataNotFoundException as e:
        logger.warning(f"No accuracy data found: {str(e)}")
        return build_error_response(e, 404)
    except Exception as e:
        logger.error(f"Error getting accuracy summary: {str(e)}", exc_info=True)
        error = InternalServerException("Failed to get accuracy summary", details={})
        return build_error_response(error, 500)


@app.route("/api/accuracy-provenance", methods=["GET"])
def get_accuracy_provenance():
    """Return detailed provenance / explanation data for accuracy submissions.

    Query Parameters:
        game_type: Optional game type filter
        draw_date: Optional draw date filter (YYYY-MM-DD) to narrow to a single submission

    Returns:
        JSON containing provenance entries with snapshot context and per-algorithm summaries.
    """
    try:
        game_type = request.args.get("game_type")
        draw_date_filter = request.args.get("draw_date")

        analyzer = AccuracyAnalyzer()
        accuracy_files = analyzer.load_all_accuracy_files(game_type)
        if not accuracy_files:
            raise DataNotFoundException(
                "No accuracy data found", details={"game_type": game_type or "all"}
            )

        # If draw_date filter applied, narrow
        if draw_date_filter:
            accuracy_files = [
                f for f in accuracy_files if f.get("draw_date") == draw_date_filter
            ]
            if not accuracy_files:
                raise DataNotFoundException(
                    "No accuracy data found for draw date",
                    details={
                        "draw_date": draw_date_filter,
                        "game_type": game_type or "all",
                    },
                )

        provenance = analyzer._build_provenance_summary(accuracy_files)

        return jsonify({"success": True, "data": provenance})
    except DataNotFoundException as e:
        logger.warning(f"No provenance data: {str(e)}")
        return build_error_response(e, 404)
    except Exception as e:
        logger.error(f"Error generating provenance: {str(e)}", exc_info=True)
        error = InternalServerException(
            "Failed to generate provenance report", details={}
        )
        return build_error_response(error, 500)


@app.route("/api/verify-result", methods=["GET"])
def verify_result_integrity():
    """Verify that a submitted draw result exists in the latest historical dataset.

    Query Parameters:
        game_type: Game type (e.g., "Lotto 6/42")
        draw_date: Draw date in YYYY-MM-DD format

    Returns:
        JSON indicating presence/absence in historical data with details.
    """
    try:
        game_type = request.args.get("game_type")
        draw_date_str = request.args.get("draw_date")

        if not game_type or not draw_date_str:
            raise BadRequestException(
                "Missing required parameters",
                details={"required": ["game_type", "draw_date"]},
            )

        validate_game_type(game_type)
        draw_date = parse_date(draw_date_str, "draw_date")

        # Locate latest result file
        data_path = config.DATA_PATH
        game_slug = game_type_to_slug(game_type)
        result_files = []

        if not os.path.exists(data_path):
            raise DataNotFoundException(
                "Data directory not found", details={"path": data_path}
            )

        for filename in os.listdir(data_path):
            if filename.startswith(f"result_{game_slug}_") and filename.endswith(
                ".json"
            ):
                filepath = os.path.join(data_path, filename)
                mtime = os.path.getmtime(filepath)
                result_files.append((filename, filepath, mtime))

        if not result_files:
            raise DataNotFoundException(
                f"No result files found for {game_type}",
                details={"game_type": game_type},
            )

        # Get latest result file
        result_files.sort(key=lambda x: x[2], reverse=True)
        latest_result_file = result_files[0][1]
        latest_result_filename = result_files[0][0]

        # Load result file
        with open(latest_result_file, "r", encoding="utf-8") as f:
            result_data = json.load(f)

        # Extract the end date from filename (e.g., result_Grand_Lotto_6-55_20251031.json -> 2025-10-31)
        # This tells us the original scrape cutoff date
        original_scrape_cutoff = None
        try:
            # Filename format: result_{game_slug}_{YYYYMMDD}.json
            filename_parts = latest_result_filename.replace(".json", "").split("_")
            if filename_parts:
                date_str = filename_parts[-1]  # Last part should be YYYYMMDD
                if len(date_str) == 8 and date_str.isdigit():
                    year = date_str[:4]
                    month = date_str[4:6]
                    day = date_str[6:8]
                    original_scrape_cutoff = datetime.strptime(
                        f"{year}-{month}-{day}", "%Y-%m-%d"
                    )
        except Exception as e:
            logger.warning(
                f"Could not parse scrape cutoff date from filename: {str(e)}"
            )

        # Search for matching draw
        pcso_format_date = draw_date.strftime("%m/%d/%Y")
        match_found = None
        is_original_scraped = False

        for draw in result_data.get("results", []):
            if draw.get("date") == pcso_format_date:
                match_found = {
                    "date": draw.get("date"),
                    "numbers": draw.get("numbers"),
                    "jackpot": draw.get("jackpot"),
                    "winners": draw.get("winners"),
                    "day_of_week": draw.get("day_of_week"),
                }

                # Check if this draw was in the original scraped data
                # If the draw date is ON OR BEFORE the original scrape cutoff date, it was originally scraped
                if original_scrape_cutoff and draw_date <= original_scrape_cutoff:
                    is_original_scraped = True

                break

        if match_found:
            return jsonify(
                {
                    "success": True,
                    "exists": True,
                    "is_original": is_original_scraped,
                    "message": f"Draw result for {draw_date_str} found in {'original scraped' if is_original_scraped else 'manually added'} data",
                    "data": {
                        "source_file": latest_result_filename,
                        "draw_details": match_found,
                        "original_cutoff_date": original_scrape_cutoff.strftime(
                            "%Y-%m-%d"
                        )
                        if original_scrape_cutoff
                        else None,
                    },
                }
            )
        else:
            return jsonify(
                {
                    "success": True,
                    "exists": False,
                    "message": f"Draw result for {draw_date_str} not found in historical data",
                    "data": {
                        "source_file": latest_result_filename,
                        "total_draws_in_file": len(result_data.get("results", [])),
                    },
                }
            )

    except (ValidationException, BadRequestException, DataNotFoundException) as e:
        logger.warning(f"Verification error: {str(e)}")
        status = 404 if isinstance(e, DataNotFoundException) else 400
        return build_error_response(e, status)
    except Exception as e:
        logger.error(f"Error verifying result integrity: {str(e)}", exc_info=True)
        error = InternalServerException("Failed to verify result integrity", details={})
        return build_error_response(error, 500)


@app.route("/api/accuracy-files", methods=["GET"])
def list_accuracy_files():
    """
    List all accuracy comparison files.

    Query Parameters:
        game_type: Optional game type filter

    Returns:
        JSON with list of accuracy files
    """
    try:
        game_type = request.args.get("game_type")

        analyzer = AccuracyAnalyzer()
        files = analyzer.load_all_accuracy_files(game_type)

        # Return simplified file list
        file_list = []
        for file_data in files:
            file_list.append(
                {
                    "filename": file_data.get("filename"),
                    "game_type": file_data.get("game_type"),
                    "draw_date": file_data.get("draw_date"),
                    "actual_numbers": file_data.get("actual_numbers"),
                    "timestamp": file_data.get("timestamp"),
                }
            )

        return jsonify({"success": True, "total": len(file_list), "data": file_list})

    except Exception as e:
        logger.error(f"Error listing accuracy files: {str(e)}", exc_info=True)
        error = InternalServerException("Failed to list accuracy files", details={})
        return build_error_response(error, 500)


@app.route("/accuracy-dashboard")
def accuracy_dashboard():
    """Render accuracy analysis dashboard."""
    try:
        analyzer = AccuracyAnalyzer()

        # Check if there's any accuracy data
        try:
            summary = analyzer.get_accuracy_summary()
            has_data = True
        except DataNotFoundException:
            has_data = False
            summary = None

        return render_template(
            "accuracy_dashboard.html", has_data=has_data, summary=summary
        )

    except Exception as e:
        logger.error(f"Error rendering accuracy dashboard: {str(e)}", exc_info=True)
        return render_template("500.html"), 500


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return render_template("500.html"), 500


if __name__ == "__main__":
    # Create data directory if it doesn't exist
    os.makedirs(config.DATA_PATH, exist_ok=True)

    # Cleanup old progress files on startup (older than 1 hour)
    try:
        cleaned = progress_tracker.cleanup_all_old_tasks(max_age_hours=1)
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old progress file(s) on startup")
    except Exception as e:
        logger.warning(f"Error cleaning up progress files on startup: {str(e)}")

    # Run the app
    logger.info(
        f"Starting Flask app on {config.HOST}:{config.PORT} (debug={config.DEBUG})"
    )
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
