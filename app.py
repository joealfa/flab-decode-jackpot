"""
Fortune Lab: Decoding the Jackpot
Main Flask Application
"""

import os
import json
import logging
import uuid
import threading
import numpy as np
from datetime import datetime
from flask import Flask, render_template, request, jsonify, make_response
from app.modules.scraper import PCSOScraper
from app.modules.analyzer import LotteryAnalyzer
from app.modules.progress_tracker import ProgressTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


app = Flask(__name__, template_folder="app/templates", static_folder="app/static")

# Configuration
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "fortune-lab-secret-key-2024")
app.config["DATA_PATH"] = "app/data"

# Initialize progress tracker
progress_tracker = ProgressTracker()


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


@app.route("/test-chart")
def test_chart():
    """Test page to verify Chart.js is working"""
    return render_template("test_chart.html")


@app.route("/")
def index():
    """Main dashboard page."""
    # Get list of available result files with metadata
    data_path = app.config["DATA_PATH"]
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
                    except (ValueError, IndexError, TypeError):
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

        scraper = PCSOScraper(headless=True)

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

    except Exception as e:
        logger.error(f"Error in scraping thread: {str(e)}", exc_info=True)
        progress_tracker.fail_task(task_id, str(e))


@app.route("/scrape", methods=["POST"])
def scrape_data():
    """
    Endpoint to trigger data scraping.
    Expects JSON with: game_type, start_date, end_date
    Returns task_id for progress tracking
    """
    logger.info("Received scrape request")

    try:
        data = request.get_json()
        logger.info(f"Request data: {data}")

        game_type = data.get("game_type")
        start_date_str = data.get("start_date")
        end_date_str = data.get("end_date")

        if not all([game_type, start_date_str, end_date_str]):
            logger.warning("Missing required fields in request")
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        # Parse dates
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        logger.info(f"Parsed dates - Start: {start_date}, End: {end_date}")

        # Validate date range
        if start_date > end_date:
            logger.warning("Invalid date range: start date is after end date")
            return jsonify(
                {"success": False, "error": "Start date must be before end date"}
            ), 400

        # Generate unique task ID
        task_id = str(uuid.uuid4())

        # Start scraping in background thread
        thread = threading.Thread(
            target=scrape_data_thread,
            args=(task_id, game_type, start_date, end_date, app.config["DATA_PATH"]),
        )
        thread.daemon = True
        thread.start()

        return jsonify(
            {"success": True, "task_id": task_id, "message": "Scraping started"}
        )

    except ValueError as e:
        logger.error(f"ValueError: {str(e)}")
        return jsonify({"success": False, "error": f"Invalid data: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Exception during scraping: {str(e)}", exc_info=True)
        return jsonify(
            {"success": False, "error": f"Error scraping data: {str(e)}"}
        ), 500


@app.route("/api/progress/<task_id>")
def get_progress(task_id):
    """Get progress for a scraping task."""
    try:
        progress = progress_tracker.get_progress(task_id)

        if not progress:
            return jsonify({"success": False, "error": "Task not found"}), 404

        # Auto-cleanup completed tasks older than 5 minutes (300 seconds)
        # This runs in background to avoid blocking the response
        threading.Thread(
            target=progress_tracker.cleanup_completed_tasks,
            args=(300,),
            daemon=True
        ).start()

        return jsonify({"success": True, "progress": progress})
    except Exception as e:
        # Log the error but don't crash - return a temporary error response
        logger.error(f"Error getting progress for task {task_id}: {str(e)}")
        return jsonify({
            "success": False, 
            "error": "Temporary error reading progress. Please try again.",
            "retry": True
        }), 500


@app.route("/analyze/<filename>")
def analyze(filename):
    """
    Run analysis and save report, then display dashboard.
    """
    try:
        # Load lottery data
        filepath = os.path.join(app.config["DATA_PATH"], filename)

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
        analysis_dir = os.path.join(app.config["DATA_PATH"], "analysis")
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

    except Exception as e:
        logger.error(f"Error analyzing data: {str(e)}", exc_info=True)
        return f"Error analyzing data: {str(e)}", 500


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """
    API endpoint to analyze a specific result file.
    Returns JSON with analysis data.
    """
    try:
        data = request.get_json()
        filename = data.get("filename")

        if not filename:
            return jsonify({"success": False, "error": "Filename is required"}), 400

        # Load data
        filepath = os.path.join(app.config["DATA_PATH"], filename)

        if not os.path.exists(filepath):
            return jsonify({"success": False, "error": "Result file not found"}), 404

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

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/files")
def api_list_files():
    """API endpoint to list all result files."""
    try:
        data_path = app.config["DATA_PATH"]
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
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analysis-history/<filename>")
def get_analysis_history(filename):
    """Get all analysis reports for a specific result file."""
    try:
        analysis_dir = os.path.join(app.config["DATA_PATH"], "analysis")

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
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/view-report/<report_filename>")
def view_report(report_filename):
    """View a specific analysis report."""
    try:
        analysis_dir = os.path.join(app.config["DATA_PATH"], "analysis")
        report_path = os.path.join(analysis_dir, report_filename)

        if not os.path.exists(report_path):
            return "Analysis report not found", 404

        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        # Load the original data file for context
        source_file = report.get("source_file")
        data_path = os.path.join(app.config["DATA_PATH"], source_file)

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

    except Exception as e:
        logger.error(f"Error viewing report: {str(e)}", exc_info=True)
        return f"Error viewing report: {str(e)}", 500


@app.route("/api/submit-actual-result", methods=["POST"])
def submit_actual_result():
    """Submit actual draw result for accuracy comparison and add to dataset."""
    try:
        data = request.get_json()

        game_type = data.get("game_type")
        draw_date_str = data.get("draw_date")
        numbers = data.get("numbers")
        jackpot = data.get("jackpot", "N/A")
        winners = data.get("winners", "N/A")

        if not all([game_type, draw_date_str, numbers]):
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        # Validate numbers
        if not isinstance(numbers, list) or len(numbers) != 6:
            return jsonify(
                {"success": False, "error": "Numbers must be an array of 6 integers"}
            ), 400

        # Parse draw date
        try:
            draw_date = datetime.strptime(draw_date_str, "%Y-%m-%d")
        except ValueError:
            return jsonify(
                {"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}
            ), 400

        # Find the latest result file for this game type
        data_path = app.config["DATA_PATH"]
        result_files = []
        game_slug = game_type.replace(" ", "_").replace("/", "-")

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

        # Get the latest result file
        result_files.sort(key=lambda x: x[2], reverse=True)
        latest_result_file = result_files[0][1]

        # Load the result file
        with open(latest_result_file, "r", encoding="utf-8") as f:
            result_data = json.load(f)

        # Create new draw entry
        actual_numbers = sorted([int(n) for n in numbers])
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
        with open(latest_result_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)

        # Load the latest analysis report for comparison
        analysis_dir = os.path.join(data_path, "analysis")
        accuracy_results = None

        if os.path.exists(analysis_dir):
            analysis_files = []

            for filename in os.listdir(analysis_dir):
                if filename.startswith(
                    f"analysis_result_{game_slug}_"
                ) and filename.endswith(".json"):
                    filepath = os.path.join(analysis_dir, filename)
                    mtime = os.path.getmtime(filepath)
                    analysis_files.append((filename, filepath, mtime))

            if analysis_files:
                # Get the latest analysis file
                analysis_files.sort(key=lambda x: x[2], reverse=True)
                latest_analysis_file = analysis_files[0][1]

                # Load the analysis
                with open(latest_analysis_file, "r", encoding="utf-8") as f:
                    analysis_data = json.load(f)

                # Perform accuracy comparison
                accuracy_results = {
                    "actual_numbers": actual_numbers,
                    "draw_date": draw_date_str,
                    "game_type": game_type,
                    "top_predictions_comparison": [],
                    "winning_predictions_comparison": [],
                    "pattern_predictions_comparison": [],
                }

                # Check top predictions
                for idx, pred in enumerate(analysis_data.get("top_predictions", []), 1):
                    predicted_numbers = sorted(pred["numbers"])
                    matches = len(set(actual_numbers) & set(predicted_numbers))

                    accuracy_results["top_predictions_comparison"].append(
                        {
                            "rank": idx,
                            "predicted_numbers": predicted_numbers,
                            "matches": matches,
                            "confidence_score": pred.get("confidence_score", 0),
                        }
                    )

                # Check winning predictions
                for idx, pred in enumerate(
                    analysis_data.get("winning_predictions", []), 1
                ):
                    predicted_numbers = sorted(pred["numbers"])
                    matches = len(set(actual_numbers) & set(predicted_numbers))

                    accuracy_results["winning_predictions_comparison"].append(
                        {
                            "rank": idx,
                            "predicted_numbers": predicted_numbers,
                            "matches": matches,
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
                    matches = len(set(actual_numbers) & set(predicted_numbers))

                    accuracy_results["pattern_predictions_comparison"].append(
                        {
                            "rank": idx,
                            "predicted_numbers": predicted_numbers,
                            "matches": matches,
                            "pattern_score": pred.get("pattern_score", 0),
                        }
                    )

                # Save accuracy results
                accuracy_dir = os.path.join(data_path, "accuracy")
                os.makedirs(accuracy_dir, exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                accuracy_filename = f"accuracy_{game_slug}_{timestamp}.json"
                accuracy_filepath = os.path.join(accuracy_dir, accuracy_filename)

                with open(accuracy_filepath, "w", encoding="utf-8") as f:
                    json.dump(accuracy_results, f, indent=2, ensure_ascii=False)

        return jsonify(
            {
                "success": True,
                "message": f"Actual result {'updated' if existing_draw is not None else 'added'} successfully",
                "accuracy_results": accuracy_results,
                "result_file": os.path.basename(latest_result_file),
                "total_draws": result_data["total_draws"],
            }
        )

    except Exception as e:
        logger.error(f"Error submitting actual result: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/delete-report/<report_filename>", methods=["DELETE"])
def delete_report(report_filename):
    """Delete an analysis report."""
    try:
        analysis_dir = os.path.join(app.config["DATA_PATH"], "analysis")
        report_path = os.path.join(analysis_dir, report_filename)

        if not os.path.exists(report_path):
            return jsonify({"success": False, "error": "Report not found"}), 404

        # Delete the file
        os.remove(report_path)
        logger.info(f"Deleted analysis report: {report_filename}")

        return jsonify({"success": True, "message": "Report deleted successfully"})

    except Exception as e:
        logger.error(f"Error deleting report: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/export-analysis/<report_filename>")
def export_analysis(report_filename):
    """Export analysis report as downloadable JSON."""
    try:
        analysis_dir = os.path.join(app.config["DATA_PATH"], "analysis")
        report_path = os.path.join(analysis_dir, report_filename)

        if not os.path.exists(report_path):
            return jsonify({"success": False, "error": "Report not found"}), 404

        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        # Create a response with proper headers for download
        response = make_response(json.dumps(report, indent=2, ensure_ascii=False))
        response.headers["Content-Type"] = "application/json"
        response.headers["Content-Disposition"] = f"attachment; filename={report_filename}"

        return response

    except Exception as e:
        logger.error(f"Error exporting analysis: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/cleanup-progress", methods=["POST"])
def cleanup_progress():
    """Manually cleanup old progress files."""
    try:
        # Accept both JSON and no body (for simple curl requests)
        data = request.get_json(silent=True) or {}
        max_age_seconds = data.get("max_age_seconds", 300)  # Default 5 minutes

        cleaned_count = progress_tracker.cleanup_completed_tasks(max_age_seconds)

        return jsonify({
            "success": True,
            "cleaned_count": cleaned_count,
            "message": f"Cleaned up {cleaned_count} progress file(s)"
        })

    except Exception as e:
        logger.error(f"Error cleaning up progress files: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


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
    os.makedirs(app.config["DATA_PATH"], exist_ok=True)

    # Cleanup old progress files on startup (older than 1 hour)
    try:
        cleaned = progress_tracker.cleanup_all_old_tasks(max_age_hours=1)
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old progress file(s) on startup")
    except Exception as e:
        logger.warning(f"Error cleaning up progress files on startup: {str(e)}")

    # Run the app
    app.run(debug=True, host="0.0.0.0", port=5000)
