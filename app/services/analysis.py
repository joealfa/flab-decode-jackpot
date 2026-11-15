"""Analysis snapshot selection independent of HTTP."""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from app.modules.analyzer import LotteryAnalyzer
from app.serialization import convert_to_serializable
from app.storage import read_json

logger = logging.getLogger(__name__)


def build_analysis_report(
    data: dict, filename: str, prediction_count: int = 5, *, comprehensive: bool = True
) -> dict:
    """Build the shared analysis payload for page and API consumers.

    Args:
        data: Loaded lottery dataset.
        filename: Source dataset name.
        prediction_count: Number of recommendations per algorithm.
        comprehensive: Include advanced sections for persisted dashboards.

    Returns:
        JSON-compatible analysis report.
    """
    analyzer = LotteryAnalyzer(data)
    report = {
        "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_file": filename,
        "game_type": data["game_type"],
        "date_range": {"start": data["start_date"], "end": data["end_date"]},
        "total_draws": len(data["results"]),
        "overall_stats": analyzer.get_overall_statistics(),
        "day_analysis": analyzer.get_all_days_analysis(),
        "top_predictions": analyzer.generate_top_predictions(top_n=prediction_count),
        "winning_predictions": analyzer.generate_winning_predictions(
            top_n=prediction_count
        ),
        "chart_data": analyzer.get_chart_data(),
    }
    if comprehensive:
        report.update(
            {
                "pattern_predictions": analyzer.generate_pattern_based_prediction(
                    top_n=prediction_count
                ),
                "pattern_analysis": analyzer.analyze_consecutive_draw_patterns(),
                "temporal_patterns": analyzer.analyze_temporal_patterns(),
                "historical_observations": analyzer.get_historical_observations(),
                "ultimate_predictions": analyzer.generate_ultimate_predictions(
                    top_n=prediction_count
                ),
            }
        )
    return convert_to_serializable(report)


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
            analysis_data = read_json(filepath)
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
