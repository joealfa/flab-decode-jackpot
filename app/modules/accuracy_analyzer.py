"""
Accuracy Analysis Module for Fortune Lab

This module provides comprehensive accuracy analysis for lottery predictions,
comparing predicted numbers against actual draw results.

Author: Fortune Lab Team
Date: October 30, 2025
"""

import json
import logging
import os
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Any

from app.config import config
from app.exceptions import DataNotFoundException, InternalServerException

logger = logging.getLogger(__name__)


class AccuracyAnalyzer:
    """
    Analyzes prediction accuracy across all lottery games.
    
    This class aggregates accuracy data from multiple submissions,
    calculates performance metrics for different prediction algorithms,
    and provides trend analysis over time.
    """

    MATCH_HIGHLIGHT_THRESHOLD = 3

    def __init__(self, accuracy_dir: Optional[str] = None):
        """
        Initialize the AccuracyAnalyzer.

        Args:
            accuracy_dir: Path to accuracy data directory. Defaults to config.ACCURACY_PATH
        """
        self.accuracy_dir = accuracy_dir or os.path.join(config.DATA_PATH, "accuracy")
        os.makedirs(self.accuracy_dir, exist_ok=True)
        logger.info(f"AccuracyAnalyzer initialized with directory: {self.accuracy_dir}")

    @staticmethod
    def _get_matched_numbers(
        comparison: Dict,
        actual_numbers: Optional[List[int]] = None
    ) -> List[int]:
        """Return matched numbers, deriving them if necessary and possible."""
        matched_numbers = comparison.get("matched_numbers")
        if isinstance(matched_numbers, list) and matched_numbers:
            return matched_numbers

        if actual_numbers is not None:
            predicted_numbers = comparison.get("predicted_numbers")
            if isinstance(predicted_numbers, list) and predicted_numbers:
                try:
                    actual_set = {int(num) for num in actual_numbers}
                    predicted_set = {int(num) for num in predicted_numbers}
                    return sorted(actual_set & predicted_set)
                except (TypeError, ValueError):
                    return []
        return []

    @staticmethod
    def _get_match_count(
        comparison: Dict,
        actual_numbers: Optional[List[int]] = None
    ) -> int:
        """Extract match count, preferring explicit or derived matched numbers."""
        matched_numbers = comparison.get("matched_numbers")
        if isinstance(matched_numbers, list):
            return len(matched_numbers)

        if actual_numbers is not None:
            derived_matches = AccuracyAnalyzer._get_matched_numbers(comparison, actual_numbers)
            if derived_matches:
                return len(derived_matches)

        matches = comparison.get("matches", 0)
        try:
            return int(matches)
        except (TypeError, ValueError):
            return 0

    def load_all_accuracy_files(self, game_type: Optional[str] = None) -> List[Dict]:
        """
        Load all accuracy comparison files.

        Args:
            game_type: Optional game type filter (e.g., "Lotto 6/42")

        Returns:
            List of accuracy comparison dictionaries

        Raises:
            InternalServerException: If file reading fails
        """
        try:
            accuracy_files = []
            
            if not os.path.exists(self.accuracy_dir):
                logger.warning(f"Accuracy directory does not exist: {self.accuracy_dir}")
                return []

            for filename in os.listdir(self.accuracy_dir):
                if not filename.endswith(".json"):
                    continue

                # Filter by game type if specified
                if game_type:
                    game_slug = game_type.replace(" ", "_").replace("/", "-")
                    if not filename.startswith(f"accuracy_{game_slug}_"):
                        continue

                filepath = os.path.join(self.accuracy_dir, filename)
                
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        data["filename"] = filename
                        data["timestamp"] = self._extract_timestamp_from_filename(filename)
                        accuracy_files.append(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in {filename}: {str(e)}")
                    continue
                except Exception as e:
                    logger.error(f"Error reading {filename}: {str(e)}")
                    continue

            # Sort by timestamp (most recent first)
            accuracy_files.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            logger.info(f"Loaded {len(accuracy_files)} accuracy files")
            return accuracy_files

        except Exception as e:
            logger.error(f"Error loading accuracy files: {str(e)}", exc_info=True)
            raise InternalServerException(
                "Failed to load accuracy files",
                details={"error": str(e)}
            )

    def analyze_overall_accuracy(self, game_type: Optional[str] = None) -> Dict:
        """
        Analyze overall prediction accuracy across all submissions.

        Args:
            game_type: Optional game type filter

        Returns:
            Dictionary containing comprehensive accuracy metrics

        Raises:
            DataNotFoundException: If no accuracy files found
            InternalServerException: If analysis fails
        """
        try:
            accuracy_files = self.load_all_accuracy_files(game_type)

            if not accuracy_files:
                raise DataNotFoundException(
                    "No accuracy data found",
                    details={"game_type": game_type or "all"}
                )

            # Initialize metrics
            metrics = {
                "total_submissions": len(accuracy_files),
                "game_type": game_type or "All Games",
                "analysis_date": datetime.now().isoformat(),
                "prediction_types": {
                    "top_predictions": self._analyze_prediction_type(
                        accuracy_files, "top_predictions_comparison"
                    ),
                    "winning_predictions": self._analyze_prediction_type(
                        accuracy_files, "winning_predictions_comparison"
                    ),
                    "pattern_predictions": self._analyze_prediction_type(
                        accuracy_files, "pattern_predictions_comparison"
                    ),
                },
                "best_performances": self._find_best_performances(accuracy_files),
                "match_distribution": self._calculate_match_distribution(accuracy_files),
                "recent_accuracy": self._calculate_recent_accuracy(accuracy_files, limit=10),
                "game_breakdown": self._calculate_game_breakdown(accuracy_files),
                "provenance": self._build_provenance_summary(accuracy_files),
            }

            # Calculate overall best algorithm
            metrics["best_algorithm"] = self._determine_best_algorithm(metrics["prediction_types"])

            logger.info(f"Completed overall accuracy analysis: {metrics['total_submissions']} submissions")
            return metrics

        except DataNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error analyzing overall accuracy: {str(e)}", exc_info=True)
            raise InternalServerException(
                "Failed to analyze accuracy",
                details={"error": str(e)}
            )

    def _analyze_prediction_type(self, accuracy_files: List[Dict], comparison_key: str) -> Dict:
        """
        Analyze accuracy for a specific prediction type.

        Args:
            accuracy_files: List of accuracy comparison data
            comparison_key: Key for prediction comparison (e.g., "top_predictions_comparison")

        Returns:
            Dictionary with prediction type metrics
        """
        total_predictions = 0
        total_matches = 0
        match_counts = defaultdict(int)  # Count of predictions with X matches
        rank_performance = defaultdict(lambda: {"total": 0, "matches": 0})
        
        for file_data in accuracy_files:
            actual_numbers = file_data.get("actual_numbers")
            comparisons = file_data.get(comparison_key, [])
            
            for comparison in comparisons:
                matches = self._get_match_count(comparison, actual_numbers)
                rank = comparison.get("rank", 0)
                
                total_predictions += 1
                total_matches += matches
                match_counts[matches] += 1
                
                rank_performance[rank]["total"] += 1
                rank_performance[rank]["matches"] += matches

        # Calculate metrics
        avg_matches = total_matches / total_predictions if total_predictions > 0 else 0
        
        # Convert match distribution to percentage
        match_distribution = {}
        for matches in range(7):  # 0-6 matches
            count = match_counts.get(matches, 0)
            percentage = (count / total_predictions * 100) if total_predictions > 0 else 0
            match_distribution[f"{matches}_matches"] = {
                "count": count,
                "percentage": round(percentage, 2)
            }

        # Analyze rank performance
        rank_stats = {}
        for rank, stats in sorted(rank_performance.items()):
            avg_rank_matches = stats["matches"] / stats["total"] if stats["total"] > 0 else 0
            rank_stats[f"rank_{rank}"] = {
                "total_predictions": stats["total"],
                "avg_matches": round(avg_rank_matches, 2)
            }

        return {
            "total_predictions": total_predictions,
            "avg_matches_per_prediction": round(avg_matches, 2),
            "match_distribution": match_distribution,
            "rank_performance": rank_stats,
            "jackpot_hits": match_counts.get(6, 0),  # 6 matches = jackpot
            "five_number_hits": match_counts.get(5, 0),
            "four_number_hits": match_counts.get(4, 0),
        }

    def _find_best_performances(self, accuracy_files: List[Dict]) -> Dict:
        """
        Find best performing predictions across all types.

        Args:
            accuracy_files: List of accuracy comparison data

        Returns:
            Dictionary with best performances
        """
        best = {
            "highest_matches": {"matches": 0, "details": None},
            "best_top_prediction": {"matches": 0, "details": None},
            "best_winning_prediction": {"matches": 0, "details": None},
            "best_pattern_prediction": {"matches": 0, "details": None},
        }

        for file_data in accuracy_files:
            draw_date = file_data.get("draw_date", "Unknown")
            game_type = file_data.get("game_type", "Unknown")
            actual = file_data.get("actual_numbers", [])
            analysis_snapshot = file_data.get("analysis_snapshot")

            # Check all prediction types
            for pred_type, key in [
                ("top", "top_predictions_comparison"),
                ("winning", "winning_predictions_comparison"),
                ("pattern", "pattern_predictions_comparison"),
            ]:
                comparisons = file_data.get(key, [])
                
                for comparison in comparisons:
                    matches = self._get_match_count(comparison, actual)
                    matched_numbers = self._get_matched_numbers(comparison, actual)
                    
                    # Update overall highest
                    if matches > best["highest_matches"]["matches"]:
                        best["highest_matches"] = {
                            "matches": matches,
                            "details": {
                                "prediction_type": pred_type,
                                "draw_date": draw_date,
                                "game_type": game_type,
                                "actual_numbers": actual,
                                "predicted_numbers": comparison.get("predicted_numbers", []),
                                "rank": comparison.get("rank", 0),
                                "matched_numbers": matched_numbers,
                                "analysis_snapshot": file_data.get("analysis_snapshot"),
                            }
                        }
                    
                    # Update type-specific best
                    best_key = f"best_{pred_type}_prediction"
                    if matches > best[best_key]["matches"]:
                        best[best_key] = {
                            "matches": matches,
                            "details": {
                                "draw_date": draw_date,
                                "game_type": game_type,
                                "actual_numbers": actual,
                                "predicted_numbers": comparison.get("predicted_numbers", []),
                                "rank": comparison.get("rank", 0),
                                "matched_numbers": matched_numbers,
                                "analysis_snapshot": analysis_snapshot,
                            }
                        }
        # Threshold logic
        threshold = self.MATCH_HIGHLIGHT_THRESHOLD
        for algo_key in ["best_top_prediction", "best_winning_prediction", "best_pattern_prediction"]:
            if best[algo_key]["matches"] < threshold:
                best[algo_key] = {"matches": 0, "details": None}

        # For highest_matches require perfect (all numbers) match
        if best["highest_matches"]["details"]:
            total_needed = len(best["highest_matches"]["details"].get("actual_numbers", [])) or 6
            if best["highest_matches"]["matches"] < total_needed:
                best["highest_matches"] = {"matches": 0, "details": None}

        return best

    def _calculate_match_distribution(self, accuracy_files: List[Dict]) -> Dict:
        """
        Calculate overall match distribution across all predictions.

        Args:
            accuracy_files: List of accuracy comparison data

        Returns:
            Dictionary with match distribution statistics
        """
        all_matches = []

        for file_data in accuracy_files:
            actual_numbers = file_data.get("actual_numbers")
            for key in ["top_predictions_comparison", "winning_predictions_comparison", 
                       "pattern_predictions_comparison"]:
                comparisons = file_data.get(key, [])
                for comparison in comparisons:
                    all_matches.append(self._get_match_count(comparison, actual_numbers))

        if not all_matches:
            return {}

        return {
            "total_predictions": len(all_matches),
            "distribution": {
                "0_matches": all_matches.count(0),
                "1_match": all_matches.count(1),
                "2_matches": all_matches.count(2),
                "3_matches": all_matches.count(3),
                "4_matches": all_matches.count(4),
                "5_matches": all_matches.count(5),
                "6_matches_jackpot": all_matches.count(6),
            },
            "average_matches": round(sum(all_matches) / len(all_matches), 2),
        }

    def _calculate_recent_accuracy(self, accuracy_files: List[Dict], limit: int = 10) -> List[Dict]:
        """
        Calculate accuracy for recent submissions.

        Args:
            accuracy_files: List of accuracy comparison data (sorted by date)
            limit: Number of recent submissions to include

        Returns:
            List of recent submission summaries
        """
        recent = []

        for file_data in accuracy_files[:limit]:
            summary = {
                "draw_date": file_data.get("draw_date", "Unknown"),
                "game_type": file_data.get("game_type", "Unknown"),
                "actual_numbers": file_data.get("actual_numbers", []),
                "best_match": 0,
                "best_prediction_type": None,
                "matched_numbers": [],
                "analysis_snapshot": file_data.get("analysis_snapshot"),
            }

            # Find best match across all prediction types
            for pred_type, key in [
                ("Top Predictions", "top_predictions_comparison"),
                ("Winning Predictions", "winning_predictions_comparison"),
                ("Pattern Predictions", "pattern_predictions_comparison"),
            ]:
                comparisons = file_data.get(key, [])
                for comparison in comparisons:
                    matches = self._get_match_count(
                        comparison,
                        summary["actual_numbers"],
                    )
                    if matches > summary["best_match"]:
                        summary["best_match"] = matches
                        summary["best_prediction_type"] = pred_type
                        summary["matched_numbers"] = self._get_matched_numbers(
                            comparison,
                            summary["actual_numbers"],
                        )

            # Apply threshold: only show best_match if >= threshold
            threshold = self.MATCH_HIGHLIGHT_THRESHOLD
            if summary["best_match"] < threshold:
                summary["best_match"] = 0
                summary["best_prediction_type"] = None
                summary["matched_numbers"] = []

            recent.append(summary)

        return recent

    def _calculate_game_breakdown(self, accuracy_files: List[Dict]) -> Dict:
        """
        Calculate accuracy breakdown by game type.

        Args:
            accuracy_files: List of accuracy comparison data

        Returns:
            Dictionary with per-game statistics
        """
        game_stats = defaultdict(lambda: {
            "submissions": 0,
            "total_predictions": 0,
            "total_matches": 0,
            "best_match": 0,
        })

        for file_data in accuracy_files:
            game = file_data.get("game_type", "Unknown")
            actual_numbers = file_data.get("actual_numbers")
            game_stats[game]["submissions"] += 1

            # Count all predictions and matches
            for key in ["top_predictions_comparison", "winning_predictions_comparison",
                       "pattern_predictions_comparison"]:
                comparisons = file_data.get(key, [])
                for comparison in comparisons:
                    matches = self._get_match_count(comparison, actual_numbers)
                    game_stats[game]["total_predictions"] += 1
                    game_stats[game]["total_matches"] += matches
                    game_stats[game]["best_match"] = max(
                        game_stats[game]["best_match"], matches
                    )

        # Calculate averages and apply threshold
        result = {}
        threshold = self.MATCH_HIGHLIGHT_THRESHOLD
        for game, stats in game_stats.items():
            avg_matches = (
                stats["total_matches"] / stats["total_predictions"]
                if stats["total_predictions"] > 0
                else 0
            )
            # Apply threshold: only show best_match if >= threshold
            best_match_display = stats["best_match"] if stats["best_match"] >= threshold else 0
            result[game] = {
                "submissions": stats["submissions"],
                "total_predictions": stats["total_predictions"],
                "avg_matches": round(avg_matches, 2),
                "best_match": best_match_display,
            }

        return result

    def _determine_best_algorithm(self, prediction_types: Dict) -> Dict:
        """
        Determine which prediction algorithm performs best overall.

        Args:
            prediction_types: Dictionary of prediction type metrics

        Returns:
            Dictionary with best algorithm information
        """
        algorithms = []

        for algo_name, metrics in prediction_types.items():
            algorithms.append({
                "name": algo_name.replace("_", " ").title(),
                "avg_matches": metrics.get("avg_matches_per_prediction", 0),
                "jackpot_hits": metrics.get("jackpot_hits", 0),
                "five_number_hits": metrics.get("five_number_hits", 0),
            })

        # Sort by average matches (primary) and jackpot hits (secondary)
        algorithms.sort(
            key=lambda x: (x["avg_matches"], x["jackpot_hits"]), reverse=True
        )

        return algorithms[0] if algorithms else {}

    def _build_provenance_summary(self, accuracy_files: List[Dict]) -> Dict:
        """Build a lightweight provenance / explanation layer.

        For each submission (accuracy file) we capture:
          - draw_date, game_type
          - snapshot metadata (generated_at, coverage_end, selection_reason if present)
          - per algorithm: best rank match summary (highest match count and which rank)
          - overall_highest_match for the submission

        This supports the forthcoming /api/accuracy-provenance endpoint and UI explanatory report.
        """
        provenance_entries: List[Dict] = []

        for file_data in accuracy_files:
            entry: Dict[str, Any] = {
                "draw_date": file_data.get("draw_date"),
                "game_type": file_data.get("game_type"),
                "actual_numbers": file_data.get("actual_numbers"),
                "snapshot": None,
                "algorithms": {},
                "overall_highest_match": 0,
            }

            snapshot = file_data.get("analysis_snapshot")
            if snapshot:
                entry["snapshot"] = {
                    "generated_at": snapshot.get("generated_at"),
                    "coverage_end": snapshot.get("coverage_end"),
                    "selection_reason": snapshot.get("selection_reason"),
                    "filename": snapshot.get("filename"),
                }

            # Iterate prediction types
            for label, key in [
                ("top", "top_predictions_comparison"),
                ("winning", "winning_predictions_comparison"),
                ("pattern", "pattern_predictions_comparison"),
            ]:
                comparisons = file_data.get(key, []) or []
                best_rank = None
                best_match = -1
                total_predictions = 0
                cumulative_matches = 0
                for comp in comparisons:
                    total_predictions += 1
                    matches = self._get_match_count(comp, file_data.get("actual_numbers"))
                    cumulative_matches += matches
                    if matches > best_match:
                        best_match = matches
                        best_rank = comp.get("rank")
                    entry["overall_highest_match"] = max(entry["overall_highest_match"], matches)
                if total_predictions:
                    entry["algorithms"][label] = {
                        "best_rank": best_rank,
                        "best_match": max(best_match, 0),
                        "avg_matches": round(cumulative_matches / total_predictions, 2),
                        "predictions": total_predictions,
                    }
            provenance_entries.append(entry)

        return {"entries": provenance_entries, "generated_at": datetime.now().isoformat()}

    def _extract_timestamp_from_filename(self, filename: str) -> str:
        """
        Extract timestamp from accuracy filename.

        Args:
            filename: Accuracy filename (e.g., "accuracy_Lotto_6-42_20251030_123456.json")

        Returns:
            Timestamp string or empty string if not found
        """
        try:
            # Expected format: accuracy_{game_slug}_{YYYYMMDD_HHMMSS}.json
            parts = filename.replace(".json", "").split("_")
            if len(parts) >= 3:
                # Last two parts should be date and time
                return f"{parts[-2]}_{parts[-1]}"
            return ""
        except Exception:
            return ""

    def get_accuracy_summary(self, game_type: Optional[str] = None) -> Dict:
        """
        Get a quick summary of accuracy metrics.

        Args:
            game_type: Optional game type filter

        Returns:
            Dictionary with summary metrics

        Raises:
            DataNotFoundException: If no accuracy files found
        """
        try:
            full_analysis = self.analyze_overall_accuracy(game_type)

            return {
                "total_submissions": full_analysis["total_submissions"],
                "game_type": full_analysis["game_type"],
                "best_algorithm": full_analysis["best_algorithm"],
                "overall_stats": {
                    "avg_matches": full_analysis["match_distribution"].get("average_matches", 0),
                    "total_predictions": full_analysis["match_distribution"].get("total_predictions", 0),
                    "jackpot_hits": full_analysis["match_distribution"]["distribution"].get("6_matches_jackpot", 0),
                    "five_number_hits": full_analysis["match_distribution"]["distribution"].get("5_matches", 0),
                },
                "best_performance": full_analysis["best_performances"]["highest_matches"],
            }

        except Exception as e:
            logger.error(f"Error getting accuracy summary: {str(e)}", exc_info=True)
            raise
