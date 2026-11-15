"""Pages HTTP routes."""

import logging
import os
from datetime import datetime

from flask import Blueprint, jsonify, render_template

from app.exceptions import (  # noqa: E402
    DataNotFoundException,
)
from app.modules.accuracy_analyzer import AccuracyAnalyzer
from app.web import (
    HTTPResponse,
    config,
)

logger = logging.getLogger(__name__)
blueprint = Blueprint("pages", __name__)


@blueprint.route("/test-chart")
def test_chart() -> HTTPResponse:
    """Test page to verify Chart.js is working"""
    return render_template("test_chart.html")


@blueprint.route("/")
def index() -> HTTPResponse:
    """Main dashboard page."""
    data_path = config.DATA_PATH
    result_files = []

    if os.path.exists(data_path):
        for filename in os.listdir(data_path):
            if filename.endswith(".json") and filename.startswith("result_"):
                parts = filename.replace("result_", "").replace(".json", "")

                parts_list = parts.split("_")
                if len(parts_list) >= 2:
                    date_str = parts_list[-1]
                    game_type_parts = parts_list[:-1]
                    game_type_raw = "_".join(game_type_parts)

                    game_type = game_type_raw.replace("_", " ").replace("-", "/")

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

    result_files.sort(key=lambda x: x["mtime"], reverse=True)

    return render_template("index.html", result_files=result_files)


@blueprint.route("/accuracy-dashboard")
def accuracy_dashboard() -> HTTPResponse:
    """Render accuracy analysis dashboard."""
    try:
        analyzer = AccuracyAnalyzer(accuracy_dir=config.ACCURACY_PATH)

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


@blueprint.route("/health")
def health() -> HTTPResponse:
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})
