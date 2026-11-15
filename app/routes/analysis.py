"""Analysis HTTP routes."""

import logging
import os
import threading
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from app.exceptions import (  # noqa: E402
    BadRequestException,
    DataNotFoundException,
    InternalServerException,
    ServiceUnavailableException,
)
from app.modules.ai_analyzer import AIAnalyzer
from app.services.ai_history import (
    create_pending_ai_analysis,
    delete_ai_analysis,
    fail_ai_analysis,
    find_pending_ai_analysis,
    list_ai_analyses,
    load_ai_analysis,
)
from app.services.analysis import build_analysis_report
from app.services.jobs import ai_analysis_thread
from app.storage import read_json, validate_filename, write_json
from app.validators import (  # noqa: E402
    require_json_body,
)
from app.web import (
    HTTPResponse,
    ai_semaphore,
    build_error_response,
    config,
)

logger = logging.getLogger(__name__)
blueprint = Blueprint("analysis", __name__)


@blueprint.route("/analyze/<filename>")
def analyze(filename: str) -> HTTPResponse:
    """
    Run analysis and save report, then display dashboard.
    """
    try:
        filepath = validate_filename(filename, config.DATA_PATH)

        if not os.path.exists(filepath):
            return "Result file not found", 404

        data = read_json(filepath)

        logger.info(f"Starting analysis for {filename}")
        analysis_report = build_analysis_report(
            data, filename, config.DEFAULT_PREDICTION_COUNT
        )

        analysis_dir = config.ANALYSIS_PATH
        os.makedirs(analysis_dir, exist_ok=True)

        base_name = filename.replace(".json", "")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        report_filename = f"analysis_{base_name}_{timestamp}.json"
        report_path = os.path.join(analysis_dir, report_filename)

        write_json(report_path, analysis_report)

        logger.info(f"Analysis report saved: {report_filename}")

        return render_template(
            "dashboard.html",
            data=data,
            filename=filename,
            report_filename=report_filename,
            **analysis_report,
        )

    except BadRequestException as e:
        return build_error_response(e, 400)
    except Exception as e:
        logger.error(f"Error analyzing data: {str(e)}", exc_info=True)
        error = InternalServerException("Analysis failed")
        return build_error_response(error, 500)


@blueprint.route("/api/analyze", methods=["POST"])
def api_analyze() -> HTTPResponse:
    """
    API endpoint to analyze a specific result file.
    Returns JSON with analysis data.
    """
    try:
        data = require_json_body(request.get_json(silent=True))
        filename = data.get("filename")

        if not filename:
            raise BadRequestException("Filename is required")

        filepath = validate_filename(filename, config.DATA_PATH)

        if not os.path.exists(filepath):
            raise DataNotFoundException(filename)

        lottery_data = read_json(filepath)

        analysis = build_analysis_report(
            lottery_data, filename, config.DEFAULT_PREDICTION_COUNT, comprehensive=False
        )

        return jsonify(
            {
                "success": True,
                "data": lottery_data,
                **{
                    key: analysis[key]
                    for key in (
                        "overall_stats",
                        "day_analysis",
                        "top_predictions",
                        "winning_predictions",
                        "chart_data",
                    )
                },
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


@blueprint.route("/api/ai-analyze", methods=["POST"])
def api_ai_analyze() -> HTTPResponse:
    """
    Queue an AI interpretation of a saved report.

    Ollama can take minutes, so the model runs in a background thread and the
    response returns 202 with the history record the browser should poll.
    """
    try:
        if not config.OLLAMA_ENABLED:
            raise BadRequestException(
                "AI analysis is not enabled. Set OLLAMA_ENABLED=True in configuration."
            )

        data = require_json_body(request.get_json(silent=True))
        analysis_filename = data.get("filename")

        if not isinstance(analysis_filename, str) or not analysis_filename:
            raise BadRequestException("Analysis filename is required")

        if analysis_filename.startswith("analysis_"):
            if not analysis_filename.endswith(".json"):
                raise BadRequestException("Invalid analysis filename")
            analysis_path = validate_filename(analysis_filename, config.ANALYSIS_PATH)
        else:
            if not analysis_filename.endswith(".json"):
                raise BadRequestException("Invalid result filename")
            validate_filename(analysis_filename, config.DATA_PATH)
            base_name = os.path.splitext(analysis_filename)[0]
            analysis_files = []

            if os.path.exists(config.ANALYSIS_PATH):
                for f in os.listdir(config.ANALYSIS_PATH):
                    if f.startswith(f"analysis_{base_name}_") and f.endswith(".json"):
                        analysis_files.append(f)

            if not analysis_files:
                raise DataNotFoundException(
                    f"No analysis found for {analysis_filename}. Please generate analysis first."
                )

            analysis_files.sort(reverse=True)
            analysis_path = validate_filename(analysis_files[0], config.ANALYSIS_PATH)

        if not os.path.exists(analysis_path):
            raise DataNotFoundException(f"Analysis file not found: {analysis_filename}")

        logger.info(f"Loading analysis for AI: {analysis_path}")

        analysis_data = read_json(analysis_path)
        report_name = os.path.basename(analysis_path)

        ai_analyzer = AIAnalyzer(settings=config)

        status = ai_analyzer.check_ollama_status()
        if not status.get("running"):
            logger.warning(f"Ollama unavailable: {status.get('error')}")
            raise ServiceUnavailableException(
                "Ollama is not running. Please start the Ollama service and try again."
            )

        if not status.get("model_available"):
            raise ServiceUnavailableException(
                f"Model '{ai_analyzer.model}' is not available in Ollama. "
                f"Run 'ollama pull {ai_analyzer.model}' or change OLLAMA_MODEL."
            )

        source_file = analysis_data.get("source_file") or ""
        if not source_file.endswith(".json"):
            source_file = report_name.removeprefix("analysis_")
        pending = find_pending_ai_analysis(
            config.AI_ANALYSIS_PATH, source_file, report_name
        )
        if pending:
            return jsonify(
                {
                    "success": True,
                    "already_pending": True,
                    "message": "This report is already being analyzed.",
                    **_job_summary(pending),
                }
            ), 202

        record = create_pending_ai_analysis(
            config.AI_ANALYSIS_PATH, report_name, analysis_data, ai_analyzer.model
        )
        try:
            threading.Thread(
                target=ai_analysis_thread,
                args=(
                    config.AI_ANALYSIS_PATH,
                    record["filename"],
                    analysis_data,
                    ai_analyzer,
                    ai_semaphore._get_current_object(),
                    config.OLLAMA_TIMEOUT,
                ),
                daemon=True,
            ).start()
        except Exception:
            fail_ai_analysis(
                config.AI_ANALYSIS_PATH,
                record["filename"],
                "AI analysis could not be started.",
            )
            raise

        logger.info(f"Queued AI analysis {record['filename']} for {report_name}")
        return jsonify(
            {
                "success": True,
                "already_pending": False,
                "message": "AI analysis started in the background.",
                **_job_summary(record),
            }
        ), 202

    except BadRequestException as e:
        logger.warning(f"Bad request in AI analyze: {str(e)}")
        return build_error_response(e, 400)
    except DataNotFoundException as e:
        logger.warning(f"Data not found in AI analyze: {str(e)}")
        return build_error_response(e, 404)
    except ServiceUnavailableException as e:
        return build_error_response(e, 503)
    except Exception as e:
        logger.error(f"Unexpected error in AI analyze: {str(e)}", exc_info=True)
        error = InternalServerException("AI analysis failed")
        return build_error_response(error, 500)


def _job_summary(record: dict) -> dict:
    """Fields the browser needs to track a background AI run."""
    return {
        key: record.get(key)
        for key in (
            "filename",
            "status",
            "created_at",
            "source_file",
            "analysis_report",
            "game_type",
            "model",
        )
    } | {"ai_filename": record.get("filename")}


@blueprint.route("/api/ollama-status", methods=["GET"])
def api_ollama_status() -> HTTPResponse:
    """Check Ollama service status."""
    try:
        ai_analyzer = AIAnalyzer(settings=config)
        status = ai_analyzer.check_ollama_status()
        return jsonify({"success": True, "status": status})
    except Exception:
        logger.error("Ollama status check failed", exc_info=True)
        return build_error_response(InternalServerException("Status check failed"), 500)


@blueprint.route("/api/analysis-history/<filename>")
def get_analysis_history(filename: str) -> HTTPResponse:
    """Get all analysis reports for a specific result file."""
    try:
        analysis_dir = config.ANALYSIS_PATH

        if not os.path.exists(analysis_dir):
            return jsonify({"success": True, "reports": []})

        base_name = filename.replace(".json", "")

        reports = []
        for report_file in os.listdir(analysis_dir):
            if report_file.startswith(
                f"analysis_{base_name}_"
            ) and report_file.endswith(".json"):
                report_path = os.path.join(analysis_dir, report_file)

                file_stat = os.stat(report_path)

                report_data = read_json(report_path)
                created_timestamp = getattr(file_stat, "st_birthtime", None)
                if created_timestamp is None:
                    created_timestamp = file_stat.st_mtime

                reports.append(
                    {
                        "filename": report_file,
                        "analyzed_at": report_data.get("analyzed_at"),
                        "created_at": datetime.fromtimestamp(
                            created_timestamp
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                        "size": file_stat.st_size,
                    }
                )

        reports.sort(key=lambda x: x["analyzed_at"], reverse=True)

        return jsonify({"success": True, "reports": reports, "count": len(reports)})

    except Exception as e:
        logger.error(f"Error getting analysis history: {str(e)}", exc_info=True)
        error = InternalServerException("Failed to get analysis history", details={})
        return build_error_response(error, 500)


@blueprint.route("/api/ai-analysis-history/<filename>")
def get_ai_analysis_history(filename: str) -> HTTPResponse:
    """List saved AI analyses for a result file, newest first."""
    try:
        validate_filename(filename, config.DATA_PATH)
        analyses = list_ai_analyses(config.AI_ANALYSIS_PATH, filename)
        return jsonify({"success": True, "analyses": analyses, "count": len(analyses)})
    except BadRequestException as e:
        return build_error_response(e, 400)
    except Exception:
        logger.error("Error getting AI analysis history", exc_info=True)
        return build_error_response(
            InternalServerException("Failed to get AI analysis history"), 500
        )


@blueprint.route("/api/ai-analysis/<ai_filename>", methods=["GET", "DELETE"])
def ai_analysis_record(ai_filename: str) -> HTTPResponse:
    """Return or delete one saved AI analysis."""
    try:
        if request.method == "DELETE":
            delete_ai_analysis(config.AI_ANALYSIS_PATH, ai_filename)
            return jsonify({"success": True, "message": "AI analysis deleted"})
        record = load_ai_analysis(config.AI_ANALYSIS_PATH, ai_filename)
        return jsonify({"success": True, "analysis": record})
    except BadRequestException as e:
        return build_error_response(e, 400)
    except DataNotFoundException as e:
        return build_error_response(e, 404)
    except Exception:
        logger.error("Error accessing AI analysis", exc_info=True)
        return build_error_response(
            InternalServerException("Failed to access AI analysis"), 500
        )


@blueprint.route("/view-report/<report_filename>")
def view_report(report_filename: str) -> HTTPResponse:
    """View a specific analysis report."""
    try:
        report_path = validate_filename(report_filename, config.ANALYSIS_PATH)

        if not os.path.exists(report_path):
            return "Analysis report not found", 404

        report = read_json(report_path)

        source_file = report.get("source_file")
        data_path = validate_filename(source_file, config.DATA_PATH)

        data = {}
        if os.path.exists(data_path):
            data = read_json(data_path)

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
