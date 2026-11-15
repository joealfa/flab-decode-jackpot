"""Management HTTP routes."""

import json
import logging
import os

from flask import Blueprint, jsonify, make_response, request

from app.exceptions import (  # noqa: E402
    BadRequestException,
    DataNotFoundException,
    InternalServerException,
    ValidationException,
)
from app.storage import read_json, validate_filename
from app.validators import (  # noqa: E402
    game_type_to_slug,
    validate_cleanup_strategy,
    validate_game_type,
)
from app.web import (
    HTTPResponse,
    build_error_response,
    config,
    progress_tracker,
)

logger = logging.getLogger(__name__)
blueprint = Blueprint("management", __name__)


@blueprint.route("/api/files")
def api_list_files() -> HTTPResponse:
    """API endpoint to list all result files."""
    try:
        data_path = config.DATA_PATH
        result_files = []

        if os.path.exists(data_path):
            for filename in os.listdir(data_path):
                if filename.endswith(".json"):
                    filepath = os.path.join(data_path, filename)

                    data = read_json(filepath)

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
        return build_error_response(error, 500)


@blueprint.route("/api/result-files")
def get_result_files_for_game() -> HTTPResponse:
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

                    data = read_json(filepath)

                    result_files.append(
                        {
                            "filename": filename,
                            "display_name": f"{data.get('game_type')} - {data.get('start_date')} to {data.get('end_date')} ({data.get('total_draws')} draws)",
                            "end_date": data.get("end_date"),
                            "total_draws": data.get("total_draws"),
                            "scraped_at": data.get("scraped_at"),
                        }
                    )

        result_files.sort(key=lambda x: x["end_date"], reverse=True)

        return jsonify({"success": True, "files": result_files})

    except (ValidationException, BadRequestException) as e:
        logger.warning(f"Validation error: {str(e)}")
        return build_error_response(e, 400)
    except Exception as e:
        logger.error(f"Error getting result files: {str(e)}", exc_info=True)
        error = InternalServerException("Failed to list result files", details={})
        return build_error_response(error, 500)


@blueprint.route("/api/delete-report/<report_filename>", methods=["DELETE"])
def delete_report(report_filename: str) -> HTTPResponse:
    """Delete an analysis report."""
    try:
        report_path = validate_filename(report_filename, config.ANALYSIS_PATH)

        if not os.path.exists(report_path):
            raise DataNotFoundException(report_filename)

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


@blueprint.route("/api/export-analysis/<report_filename>")
def export_analysis(report_filename: str) -> HTTPResponse:
    """Export analysis report as downloadable JSON."""
    try:
        report_path = validate_filename(report_filename, config.ANALYSIS_PATH)

        if not os.path.exists(report_path):
            raise DataNotFoundException(report_filename)

        report = read_json(report_path)

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


@blueprint.route("/api/cleanup-progress", methods=["POST"])
def cleanup_progress() -> HTTPResponse:
    """Manually cleanup old progress files with detailed results."""
    try:
        data = request.get_json(silent=True) or {}

        strategy = validate_cleanup_strategy(data.get("strategy", "all"))

        if strategy == "all":
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
