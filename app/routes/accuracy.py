"""Accuracy HTTP routes."""

import logging
import os
from datetime import datetime

from flask import Blueprint, jsonify, request

from app.exceptions import (  # noqa: E402
    BadRequestException,
    DataNotFoundException,
    InternalServerException,
    ValidationException,
)
from app.modules.accuracy_analyzer import AccuracyAnalyzer
from app.services.analysis import select_analysis_snapshot
from app.services.results import submit_draw
from app.storage import read_json, validate_filename, write_json
from app.validators import (  # noqa: E402
    game_type_to_slug,
    normalize_winner_count,
    parse_date,
    require_fields,
    require_json_body,
    validate_game_type,
    validate_lottery_numbers,
)
from app.web import (
    HTTPResponse,
    build_error_response,
    config,
)

logger = logging.getLogger(__name__)
blueprint = Blueprint("accuracy", __name__)


@blueprint.route("/api/submit-actual-result", methods=["POST"])
def submit_actual_result() -> HTTPResponse:
    """Submit actual draw result for accuracy comparison and add to dataset."""
    try:
        data = require_json_body(request.get_json())

        require_fields(data, ["game_type", "draw_date", "numbers"])
        game_type = validate_game_type(data["game_type"])
        draw_date = parse_date(data["draw_date"], "draw_date")
        actual_numbers = validate_lottery_numbers(data["numbers"], game_type)

        jackpot = data.get("jackpot", "N/A")
        winner_count = normalize_winner_count(data.get("winners"))
        winners = str(winner_count) if winner_count is not None else "N/A"
        target_filename = data.get("target_filename")
        draw_date_str = data["draw_date"]

        data_path = config.DATA_PATH
        result_files = []
        game_slug = game_type_to_slug(game_type)

        for filename in os.listdir(data_path):
            if filename.startswith(f"result_{game_slug}_") and filename.endswith(
                ".json"
            ):
                filepath = validate_filename(filename, data_path)
                mtime = os.path.getmtime(filepath)
                result_files.append((filename, filepath, mtime))

        if not result_files:
            return jsonify(
                {"success": False, "error": f"No result files found for {game_type}"}
            ), 404

        if target_filename:
            if not isinstance(target_filename, str):
                raise BadRequestException("Invalid target filename")
            target_file = validate_filename(target_filename, data_path)
            allowed_result_paths = {
                os.path.realpath(path) for _, path, _ in result_files
            }
            if target_file not in allowed_result_paths:
                raise BadRequestException(
                    "Target file must be a result file for the selected game"
                )
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
            result_files.sort(key=lambda x: x[2], reverse=True)
            result_file_path = result_files[0][1]
            logger.info(f"Using latest file: {result_files[0][0]}")

        new_draw = {
            "game": game_type,
            "date": draw_date.strftime("%m/%d/%Y"),
            "day_of_week": draw_date.strftime("%A"),
            "numbers": actual_numbers,
            "jackpot": jackpot,
            "winners": winners,
        }

        result_data, was_updated = submit_draw(result_file_path, game_type, new_draw)

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

                accuracy_results = {
                    "actual_numbers": actual_numbers,
                    "draw_date": draw_date_str,
                    "game_type": game_type,
                    "top_predictions_comparison": [],
                    "winning_predictions_comparison": [],
                    "pattern_predictions_comparison": [],
                    "ultimate_predictions_comparison": [],
                    "comparison_interpretation": (
                        "Descriptive saved-pick comparison, not a controlled walk-forward evaluation. "
                        "Snapshot dates alone cannot prove predictions were made before the outcome."
                    ),
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
                        "timing_status": (
                            "earlier_day_snapshot"
                            if analysis_generated_at
                            and coverage_end
                            and analysis_generated_at.date() < draw_date.date()
                            and coverage_end < draw_date.date()
                            else "retrospective_or_unverified"
                        ),
                    },
                }

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

                for idx, pred in enumerate(
                    analysis_data.get("ultimate_predictions", []), 1
                ):
                    predicted_numbers = sorted(pred["numbers"])
                    matched_numbers = sorted(
                        set(actual_numbers) & set(predicted_numbers)
                    )
                    accuracy_results["ultimate_predictions_comparison"].append(
                        {
                            "rank": idx,
                            "predicted_numbers": predicted_numbers,
                            "matches": len(matched_numbers),
                            "matched_numbers": matched_numbers,
                            "ultimate_confidence_score": pred.get(
                                "ultimate_confidence_score", 0
                            ),
                        }
                    )

                accuracy_dir = config.ACCURACY_PATH
                os.makedirs(accuracy_dir, exist_ok=True)

                # Remove outdated snapshots for the same draw to avoid confusion
                for existing_filename in os.listdir(accuracy_dir):
                    if not existing_filename.startswith(
                        f"accuracy_{game_slug}_"
                    ) or not existing_filename.endswith(".json"):
                        continue

                    existing_path = os.path.join(accuracy_dir, existing_filename)
                    try:
                        existing_data = read_json(existing_path)
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
                accuracy_filename = (
                    f"accuracy_{game_slug}_{draw_date:%Y%m%d}_{timestamp}.json"
                )
                accuracy_filepath = os.path.join(accuracy_dir, accuracy_filename)

                write_json(accuracy_filepath, accuracy_results)
            else:
                logger.warning(
                    "No suitable analysis snapshot found for %s on %s",
                    game_type,
                    draw_date_str,
                )

        return jsonify(
            {
                "success": True,
                "message": f"Actual result {'updated' if was_updated else 'added'} successfully",
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


@blueprint.route("/api/accuracy-analysis", methods=["GET"])
def get_accuracy_analysis() -> HTTPResponse:
    """
    Get comprehensive accuracy analysis.

    Query Parameters:
        game_type: Optional game type filter (e.g., "Lotto 6/42")

    Returns:
        JSON with complete accuracy analysis
    """
    try:
        game_type = request.args.get("game_type")

        analyzer = AccuracyAnalyzer(accuracy_dir=config.ACCURACY_PATH)
        analysis = analyzer.analyze_overall_accuracy(game_type)

        return jsonify({"success": True, "data": analysis})

    except DataNotFoundException as e:
        logger.warning(f"No accuracy data found: {str(e)}")
        return build_error_response(e, 404)
    except Exception as e:
        logger.error(f"Error analyzing accuracy: {str(e)}", exc_info=True)
        error = InternalServerException("Failed to analyze accuracy", details={})
        return build_error_response(error, 500)


@blueprint.route("/api/accuracy-summary", methods=["GET"])
def get_accuracy_summary() -> HTTPResponse:
    """
    Get quick accuracy summary.

    Query Parameters:
        game_type: Optional game type filter

    Returns:
        JSON with summary metrics
    """
    try:
        game_type = request.args.get("game_type")

        analyzer = AccuracyAnalyzer(accuracy_dir=config.ACCURACY_PATH)
        summary = analyzer.get_accuracy_summary(game_type)

        return jsonify({"success": True, "data": summary})

    except DataNotFoundException as e:
        logger.warning(f"No accuracy data found: {str(e)}")
        return build_error_response(e, 404)
    except Exception as e:
        logger.error(f"Error getting accuracy summary: {str(e)}", exc_info=True)
        error = InternalServerException("Failed to get accuracy summary", details={})
        return build_error_response(error, 500)


@blueprint.route("/api/accuracy-provenance", methods=["GET"])
def get_accuracy_provenance() -> HTTPResponse:
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

        analyzer = AccuracyAnalyzer(accuracy_dir=config.ACCURACY_PATH)
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


@blueprint.route("/api/verify-result", methods=["GET"])
def verify_result_integrity() -> HTTPResponse:
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

        result_files.sort(key=lambda x: x[2], reverse=True)
        latest_result_file = result_files[0][1]
        latest_result_filename = result_files[0][0]

        result_data = read_json(latest_result_file)

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


@blueprint.route("/api/accuracy-files", methods=["GET"])
def list_accuracy_files() -> HTTPResponse:
    """
    List all accuracy comparison files.

    Query Parameters:
        game_type: Optional game type filter

    Returns:
        JSON with list of accuracy files
    """
    try:
        game_type = request.args.get("game_type")

        analyzer = AccuracyAnalyzer(accuracy_dir=config.ACCURACY_PATH)
        files = analyzer.load_all_accuracy_files(game_type)

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
