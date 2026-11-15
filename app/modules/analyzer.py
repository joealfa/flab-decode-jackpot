"""
Lottery Data Analysis Module
Summarizes historical draws and ranks heuristic number combinations.
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime
from math import comb
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from app.exceptions import DataValidationException, InsufficientDataException
from app.validators import (
    GAME_MAX_NUMBERS,
    NUMBERS_PER_DRAW,
    normalize_winner_count,
    validate_game_type,
    validate_lottery_numbers,
)

logger = logging.getLogger(__name__)


class LotteryAnalyzer:
    """Analyze historical lottery data and generate heuristic combinations."""

    DAYS_OF_WEEK = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    ANALYSIS_VERSION = "2"

    def __init__(self, data: Dict, *, rng: np.random.Generator | None = None):
        """
        Initialize analyzer with lottery data.

        Args:
            data: Dictionary containing lottery results
            rng: Optional local generator for reproducible sampling.
        """
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise DataValidationException("Dataset must contain a results list")
        self.game_type = validate_game_type(data.get("game_type", ""))
        self.max_number = GAME_MAX_NUMBERS[self.game_type]
        self.numbers_to_pick = NUMBERS_PER_DRAW
        self.rng = rng if rng is not None else np.random.default_rng()
        self.input_quality = {
            "source_records": len(data["results"]),
            "duplicate_records_removed": 0,
            "weekday_labels_corrected": 0,
            "game_labels_normalized": 0,
            "unknown_winner_counts": 0,
        }
        self.results = self._prepare_results(data["results"])
        if not self.results:
            raise InsufficientDataException("At least one valid draw is required")
        self.data = {
            **data,
            "results": self.results,
            "total_draws": len(self.results),
            "start_date": datetime.strptime(
                self.results[-1]["date"], "%m/%d/%Y"
            ).strftime("%Y-%m-%d"),
            "end_date": datetime.strptime(self.results[0]["date"], "%m/%d/%Y").strftime(
                "%Y-%m-%d"
            ),
        }
        self.number_frequency = self._frequency(self.results)
        self.winning_draws = [
            r for r in self.results if r["winners"] not in {"0", "N/A"}
        ]
        self._temporal_patterns: Dict | None = None
        self.df = self._create_dataframe()

    def _prepare_results(self, records: List[Dict]) -> List[Dict]:
        draws = {}
        for index, result in enumerate(records):
            if not isinstance(result, dict) or not isinstance(result.get("date"), str):
                raise DataValidationException(
                    f"Invalid draw record at position {index + 1}"
                )
            raw_date = result["date"]
            try:
                date = datetime.strptime(raw_date, "%m/%d/%Y")
            except ValueError:
                try:
                    date = datetime.strptime(raw_date, "%Y-%m-%d")
                except ValueError as exc:
                    raise DataValidationException(
                        f"Invalid draw date: {raw_date}"
                    ) from exc
            source_game = result.get("game", self.game_type)
            if (
                not isinstance(source_game, str)
                or "".join(source_game.split()).casefold()
                != "".join(self.game_type.split()).casefold()
            ):
                raise DataValidationException(
                    f"Draw on {raw_date} belongs to another game"
                )
            if source_game != self.game_type:
                self.input_quality["game_labels_normalized"] += 1
            numbers = validate_lottery_numbers(result.get("numbers"), self.game_type)
            winner_count = normalize_winner_count(result.get("winners"))
            weekday = date.strftime("%A")
            if result.get("day_of_week") != weekday:
                self.input_quality["weekday_labels_corrected"] += 1
            draw = {
                **result,
                "date": date.strftime("%m/%d/%Y"),
                "day_of_week": weekday,
                "numbers": numbers,
                "game": self.game_type,
                "winners": str(winner_count) if winner_count is not None else "N/A",
            }
            existing = draws.get(date)
            if existing is not None:
                if any(
                    existing.get(key) != draw.get(key)
                    for key in ("numbers", "winners", "jackpot")
                ):
                    raise DataValidationException(
                        f"Conflicting duplicate draw on {draw['date']}"
                    )
                self.input_quality["duplicate_records_removed"] += 1
                continue
            draws[date] = draw
            self.input_quality["unknown_winner_counts"] += winner_count is None
        if any(
            self.input_quality[key]
            for key in (
                "duplicate_records_removed",
                "weekday_labels_corrected",
                "game_labels_normalized",
            )
        ):
            logger.warning(
                "Normalized %s analysis dataset: %s", self.game_type, self.input_quality
            )
        return [draws[date] for date in sorted(draws, reverse=True)]

    def _frequency(self, draws: List[Dict]) -> Counter:
        frequency = Counter({number: 0 for number in range(1, self.max_number + 1)})
        frequency.update(number for draw in draws for number in draw["numbers"])
        return frequency

    def _sample_combination(self, scores: Dict, noise: float) -> Tuple:
        numbers = np.array(sorted(scores), dtype=int)
        weights = np.array([scores[int(n)] for n in numbers], dtype=float)
        weights += self.rng.random(len(numbers)) * noise
        if not np.isfinite(weights).all() or (weights < 0).any() or weights.sum() <= 0:
            raise DataValidationException(
                "Combination sampling weights must be finite and nonnegative"
            )
        chosen = self.rng.choice(
            numbers, size=self.numbers_to_pick, replace=False, p=weights / weights.sum()
        )
        return tuple(sorted(int(number) for number in chosen))

    def _validate_prediction_count(self, top_n: int) -> None:
        if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
            raise DataValidationException(
                "Combination count must be a positive integer"
            )
        if top_n > comb(self.max_number, self.numbers_to_pick):
            raise DataValidationException(
                "Combination count exceeds the available unique combinations"
            )

    def _create_dataframe(self) -> pd.DataFrame:
        """Create pandas DataFrame from results."""
        if not self.results:
            return pd.DataFrame()

        df = pd.DataFrame(self.results)
        df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y")
        return df

    def get_overall_statistics(self) -> Dict:
        """
        Calculate overall statistics for all draws.

        Returns:
            Dictionary containing various statistics
        """
        if self.df.empty:
            return {}

        # Flatten all numbers
        number_freq = self.number_frequency

        # Calculate statistics
        stats = {
            "total_draws": len(self.results),
            "date_range": {
                "start": self.data["start_date"],
                "end": self.data["end_date"],
            },
            "most_frequent_numbers": sorted(
                number_freq.items(), key=lambda x: x[1], reverse=True
            )[:10],
            "least_frequent_numbers": sorted(number_freq.items(), key=lambda x: x[1])[
                :10
            ],
            "number_frequency": dict(number_freq),
            "average_frequency": np.mean(list(number_freq.values())),
            "hot_numbers": self._get_hot_numbers(number_freq, top_n=10),
            "cold_numbers": self._get_cold_numbers(number_freq, top_n=10),
            "even_odd_analysis": self._analyze_even_odd(),
            "high_low_analysis": self._analyze_high_low(),
            "consecutive_analysis": self._analyze_consecutive_numbers(),
            "sum_analysis": self._analyze_sum_ranges(),
            "winner_analysis": self.get_winner_analysis(),
            "frequency_context": self._frequency_context(self.results),
            "fair_draw_baseline": {
                "jackpot_combinations": comb(self.max_number, self.numbers_to_pick),
                "expected_carryover": self.numbers_to_pick**2 / self.max_number,
                "interpretation": "Every particular valid combination has the same jackpot probability under a fair independent draw.",
            },
            "data_quality": self.input_quality,
        }

        return stats

    def get_day_specific_analysis(self, day: str) -> Dict:
        """
        Analyze draws for a specific day of the week.

        Args:
            day: Day of the week (e.g., 'Monday')

        Returns:
            Dictionary containing day-specific statistics
        """
        if day not in self.DAYS_OF_WEEK:
            raise ValueError(f"Invalid day. Must be one of: {self.DAYS_OF_WEEK}")

        # Filter results for specific day
        day_results = [r for r in self.results if r["day_of_week"] == day]

        if not day_results:
            return {
                "day": day,
                "total_draws": 0,
                "message": f"No draws found for {day}",
            }

        # Flatten numbers for this day
        number_freq = self._frequency(day_results)

        stats = {
            "day": day,
            "total_draws": len(day_results),
            "most_frequent_numbers": sorted(
                number_freq.items(), key=lambda x: x[1], reverse=True
            )[:10],
            "number_frequency": dict(number_freq),
            "hot_numbers": self._get_hot_numbers(number_freq, top_n=6),
            "frequency_context": self._frequency_context(day_results),
            "predicted_combinations": self._generate_predictions_for_day(
                day_results, top_n=5
            ),
        }

        return stats

    def get_all_days_analysis(self) -> Dict:
        """
        Get analysis for all days of the week.

        Returns:
            Dictionary with analysis for each day
        """
        return {day: self.get_day_specific_analysis(day) for day in self.DAYS_OF_WEEK}

    def _get_hot_numbers(self, freq: Counter, top_n: int = 10) -> List[int]:
        """Get the most frequently drawn numbers."""
        return [num for num, count in freq.most_common() if count > 0][:top_n]

    def _get_cold_numbers(self, freq: Counter, top_n: int = 10) -> List[int]:
        """Get the least frequently drawn numbers."""
        return sorted(range(1, self.max_number + 1), key=lambda n: (freq.get(n, 0), n))[
            :top_n
        ]

    def _frequency_context(self, draws: List[Dict]) -> Dict:
        frequency = self._frequency(draws)
        count = len(draws)
        expected_rate = self.numbers_to_pick / self.max_number
        z = 1.959963984540054
        intervals = {}
        for number, appearances in frequency.items():
            rate = appearances / count
            denominator = 1 + z * z / count
            center = (rate + z * z / (2 * count)) / denominator
            half_width = (
                z
                * np.sqrt(rate * (1 - rate) / count + z * z / (4 * count * count))
                / denominator
            )
            intervals[number] = {
                "count": appearances,
                "appearance_rate": round(rate, 6),
                "wilson_95_interval": [
                    round(max(0.0, center - half_width), 6),
                    round(min(1.0, center + half_width), 6),
                ],
            }
        return {
            "sample_size": count,
            "expected_appearance_rate": expected_rate,
            "expected_frequency": count * expected_rate,
            "number_statistics": intervals,
            "interval_note": "Pointwise 95% Wilson intervals, not simultaneous significance tests. Rankings are descriptive; examining many numbers can reveal chance fluctuations.",
        }

    def _analyze_even_odd(self) -> Dict:
        """Analyze even/odd number distribution."""
        even_odd_patterns = defaultdict(int)

        for result in self.results:
            even_count = sum(1 for num in result["numbers"] if num % 2 == 0)
            odd_count = len(result["numbers"]) - even_count
            pattern = f"{even_count}E-{odd_count}O"
            even_odd_patterns[pattern] += 1

        return {
            "patterns": dict(even_odd_patterns),
            "most_common_pattern": max(even_odd_patterns.items(), key=lambda x: x[1])[
                0
            ],
            "expected_pattern_probabilities": {
                f"{even}E-{self.numbers_to_pick - even}O": (
                    comb(self.max_number // 2, even)
                    * comb(
                        self.max_number - self.max_number // 2,
                        self.numbers_to_pick - even,
                    )
                    / comb(self.max_number, self.numbers_to_pick)
                )
                for even in range(self.numbers_to_pick + 1)
            },
        }

    def _analyze_high_low(self) -> Dict:
        """Analyze high/low number distribution."""
        mid_point = self.max_number // 2
        high_low_patterns = defaultdict(int)

        for result in self.results:
            low_count = sum(1 for num in result["numbers"] if num <= mid_point)
            high_count = len(result["numbers"]) - low_count
            pattern = f"{low_count}L-{high_count}H"
            high_low_patterns[pattern] += 1

        return {
            "patterns": dict(high_low_patterns),
            "most_common_pattern": max(high_low_patterns.items(), key=lambda x: x[1])[
                0
            ],
            "mid_point": mid_point,
        }

    def _analyze_consecutive_numbers(self) -> Dict:
        """Analyze consecutive number patterns."""
        consecutive_stats = []

        for result in self.results:
            sorted_nums = sorted(result["numbers"])
            consecutive_count = 0

            for i in range(len(sorted_nums) - 1):
                if sorted_nums[i + 1] - sorted_nums[i] == 1:
                    consecutive_count += 1

            consecutive_stats.append(consecutive_count)

        return {
            "average_consecutive": np.mean(consecutive_stats),
            "max_consecutive": max(consecutive_stats),
            "draws_with_consecutive": sum(1 for c in consecutive_stats if c > 0),
            "percentage_with_consecutive": (
                sum(1 for c in consecutive_stats if c > 0) / len(consecutive_stats)
            )
            * 100,
            "expected_percentage_with_consecutive": (
                1
                - comb(self.max_number - self.numbers_to_pick + 1, self.numbers_to_pick)
                / comb(self.max_number, self.numbers_to_pick)
            )
            * 100,
        }

    def _analyze_sum_ranges(self) -> Dict:
        """Analyze sum of numbers in draws."""
        sums = [sum(result["numbers"]) for result in self.results]

        return {
            "average_sum": np.mean(sums),
            "min_sum": min(sums),
            "max_sum": max(sums),
            "median_sum": np.median(sums),
            "std_dev": np.std(sums),
            "expected_average_sum": self.numbers_to_pick * (self.max_number + 1) / 2,
            "expected_std_dev": np.sqrt(
                self.numbers_to_pick
                * (self.max_number + 1)
                * (self.max_number - self.numbers_to_pick)
                / 12
            ),
        }

    def generate_top_predictions(self, top_n: int = 5) -> List[Dict]:
        """
        Generate top N predicted combinations based on overall analysis.

        Args:
            top_n: Number of predictions to generate

        Returns:
            List of predicted combinations with scores
        """
        self._validate_prediction_count(top_n)
        number_freq = self.number_frequency

        # Calculate weighted scores for each number
        max_freq = max(number_freq.values())
        number_scores = {
            num: freq / max_freq if freq else 0.1 for num, freq in number_freq.items()
        }

        # Generate combinations using weighted random selection
        predictions = []
        seen_combinations = set()

        attempts = 0
        max_attempts = top_n * 100

        while len(predictions) < top_n and attempts < max_attempts:
            attempts += 1

            combo = self._sample_combination(number_scores, noise=0.3)

            if combo not in seen_combinations:
                seen_combinations.add(combo)

                score = self._calculate_combination_score(combo, number_scores)

                predictions.append(
                    {
                        "numbers": list(combo),
                        "confidence_score": round(score, 2),
                        "analysis": self._analyze_combination(combo),
                    }
                )

        predictions.sort(key=lambda x: x["confidence_score"], reverse=True)

        return predictions[:top_n]

    def _generate_predictions_for_day(
        self, day_results: List[Dict], top_n: int = 5
    ) -> List[Dict]:
        """Generate predictions specific to a day of the week."""
        self._validate_prediction_count(top_n)
        if not day_results:
            return []

        number_freq = self._frequency(day_results)

        max_freq = max(number_freq.values()) if number_freq else 1
        number_scores = {
            num: freq / max_freq if freq else 0.1 for num, freq in number_freq.items()
        }

        predictions = []
        seen_combinations = set()
        attempts = 0
        max_attempts = top_n * 100

        while len(predictions) < top_n and attempts < max_attempts:
            attempts += 1

            combo = self._sample_combination(number_scores, noise=0.3)

            if combo not in seen_combinations:
                seen_combinations.add(combo)
                score = self._calculate_combination_score(combo, number_scores)

                predictions.append(
                    {"numbers": list(combo), "confidence_score": round(score, 2)}
                )

        predictions.sort(key=lambda x: x["confidence_score"], reverse=True)
        return predictions[:top_n]

    def _calculate_combination_score(self, combo: Tuple, number_scores: Dict) -> float:
        """Calculate historical-pattern points, not a winning probability."""
        # Base score from number frequencies
        base_score = sum(number_scores.get(num, 0) for num in combo) / len(combo)

        # Bonus for balanced even/odd
        even_count = sum(1 for num in combo if num % 2 == 0)
        balance_bonus = 1.0 - abs(even_count - len(combo) / 2) / len(combo)

        # Bonus for spread across range
        spread = (max(combo) - min(combo)) / self.max_number
        spread_bonus = spread * 0.5

        total_score = (base_score * 0.6) + (balance_bonus * 0.2) + (spread_bonus * 0.2)

        return min(total_score * 100, 100)  # Scale to 0-100

    def _analyze_combination(self, combo: Tuple) -> Dict:
        """Analyze a combination for various patterns."""
        even_count = sum(1 for num in combo if num % 2 == 0)
        odd_count = len(combo) - even_count

        mid_point = self.max_number // 2
        low_count = sum(1 for num in combo if num <= mid_point)
        high_count = len(combo) - low_count

        sorted_combo = sorted(combo)
        consecutive = sum(
            1
            for i in range(len(sorted_combo) - 1)
            if sorted_combo[i + 1] - sorted_combo[i] == 1
        )

        return {
            "even_odd": f"{even_count}E-{odd_count}O",
            "high_low": f"{low_count}L-{high_count}H",
            "sum": int(sum(combo)),  # Convert to native int
            "consecutive_pairs": int(consecutive),  # Convert to native int
        }

    def _get_recent_pattern_preference(self, pattern_type: str) -> str:
        """Get the most common pattern from recent draws."""
        recent_draws = self.results[:20]

        if pattern_type == "even_odd":
            patterns = []
            for result in recent_draws:
                even_count = sum(1 for num in result["numbers"] if num % 2 == 0)
                odd_count = len(result["numbers"]) - even_count
                patterns.append(f"{even_count}E-{odd_count}O")
            return Counter(patterns).most_common(1)[0][0]

        elif pattern_type == "high_low":
            mid_point = self.max_number // 2
            patterns = []
            for result in recent_draws:
                low_count = sum(1 for num in result["numbers"] if num <= mid_point)
                high_count = len(result["numbers"]) - low_count
                patterns.append(f"{low_count}L-{high_count}H")
            return Counter(patterns).most_common(1)[0][0]

        return ""

    def get_winner_analysis(self) -> Dict:
        """
        Analyze draws that had winners.

        Returns:
            Dictionary containing winner-specific statistics
        """
        # Filter results that have winners (not "0" or "N/A")
        winning_draws = self.winning_draws

        if not winning_draws:
            return {
                "total_winning_draws": 0,
                "message": "No winning draws found in the dataset",
            }

        # Analyze winning numbers
        winning_numbers = [num for result in winning_draws for num in result["numbers"]]
        winning_number_freq = Counter(winning_numbers)

        # Analyze winning dates
        winning_dates = [
            datetime.strptime(r["date"], "%m/%d/%Y")
            if isinstance(r["date"], str)
            else r["date"]
            for r in winning_draws
        ]
        winning_days = [r["day_of_week"] for r in winning_draws]
        winning_day_freq = Counter(winning_days)

        # Analyze winning months
        winning_months = [d.month for d in winning_dates]
        winning_month_freq = Counter(winning_months)

        # Analyze jackpot amounts (if numeric)
        jackpot_amounts = []
        for r in winning_draws:
            jackpot = r.get("jackpot", "N/A")
            if jackpot and jackpot != "N/A":
                # Try to extract numeric value
                try:
                    # Remove commas and PHP symbol
                    clean_jackpot = (
                        str(jackpot)
                        .replace(",", "")
                        .replace("₱", "")
                        .replace("PHP", "")
                        .strip()
                    )
                    amount = float(clean_jackpot)
                    if not np.isfinite(amount) or amount < 0:
                        raise ValueError(
                            "Jackpot amount must be finite and nonnegative"
                        )
                    jackpot_amounts.append(amount)
                except ValueError, AttributeError:
                    logger.warning(
                        "Ignoring unparseable jackpot amount on %s: %r",
                        r["date"],
                        jackpot,
                    )

        analysis = {
            "total_winning_draws": len(winning_draws),
            "win_rate": round((len(winning_draws) / len(self.results)) * 100, 2),
            "known_winner_draws": len(self.results)
            - self.input_quality["unknown_winner_counts"],
            "interpretation": "Share of recorded draws with known jackpot winners, not a ticket's winning probability. Unknown winner counts remain in the total-draw denominator.",
            # Most frequent winning numbers
            "most_frequent_winning_numbers": sorted(
                winning_number_freq.items(), key=lambda x: x[1], reverse=True
            )[:10],
            # Hot winning numbers
            "hot_winning_numbers": self._get_hot_numbers(winning_number_freq, top_n=10),
            # Day of week analysis for wins
            "winning_days_frequency": dict(winning_day_freq),
            "best_winning_days": sorted(
                winning_day_freq.items(), key=lambda x: x[1], reverse=True
            )[:3],
            # Month analysis for wins
            "winning_months_frequency": dict(winning_month_freq),
            "best_winning_months": sorted(
                winning_month_freq.items(), key=lambda x: x[1], reverse=True
            )[:3],
            # Winning patterns
            "winning_even_odd_patterns": self._analyze_pattern_for_draws(
                winning_draws, "even_odd"
            ),
            "winning_high_low_patterns": self._analyze_pattern_for_draws(
                winning_draws, "high_low"
            ),
            # Jackpot statistics (if available)
            "jackpot_stats": {
                "count": len(jackpot_amounts),
                "average": round(np.mean(jackpot_amounts), 2) if jackpot_amounts else 0,
                "min": round(min(jackpot_amounts), 2) if jackpot_amounts else 0,
                "max": round(max(jackpot_amounts), 2) if jackpot_amounts else 0,
            }
            if jackpot_amounts
            else None,
            "next_win_probability": self._predict_next_win_probability(winning_draws),
        }

        return analysis

    def _analyze_pattern_for_draws(self, draws: List[Dict], pattern_type: str) -> Dict:
        """Analyze even/odd or high/low patterns for specific draws."""
        patterns = defaultdict(int)

        if pattern_type == "even_odd":
            for result in draws:
                even_count = sum(1 for num in result["numbers"] if num % 2 == 0)
                odd_count = len(result["numbers"]) - even_count
                pattern = f"{even_count}E-{odd_count}O"
                patterns[pattern] += 1

        elif pattern_type == "high_low":
            mid_point = self.max_number // 2
            for result in draws:
                low_count = sum(1 for num in result["numbers"] if num <= mid_point)
                high_count = len(result["numbers"]) - low_count
                pattern = f"{low_count}L-{high_count}H"
                patterns[pattern] += 1

        if patterns:
            most_common = max(patterns.items(), key=lambda x: x[1])
            return {
                "patterns": dict(patterns),
                "most_common_pattern": most_common[0],
                "most_common_count": most_common[1],
            }
        return {"patterns": {}, "most_common_pattern": None}

    def _predict_next_win_probability(self, winning_draws: List[Dict]) -> Dict:
        """
        Predict probability patterns for next potential win.

        Returns:
            Historical win-interval estimates
        """
        if not winning_draws:
            return {}

        # Analyze time gaps between wins
        winning_dates = []
        for r in winning_draws:
            try:
                if isinstance(r["date"], str):
                    date = datetime.strptime(r["date"], "%m/%d/%Y")
                else:
                    date = r["date"]
                winning_dates.append(date)
            except ValueError, KeyError:
                continue

        winning_dates.sort()

        # Calculate days between wins
        if len(winning_dates) > 1:
            gaps = [
                (winning_dates[i + 1] - winning_dates[i]).days
                for i in range(len(winning_dates) - 1)
            ]

            avg_gap = np.mean(gaps)
            median_gap = np.median(gaps)
            std_gap = np.std(gaps)

            last_win = winning_dates[-1]
            observation_end = datetime.strptime(self.results[0]["date"], "%m/%d/%Y")
            days_since_last_win = (observation_end - last_win).days

            return {
                "average_days_between_wins": round(avg_gap, 1),
                "median_days_between_wins": round(median_gap, 1),
                "std_dev_days": round(std_gap, 1),
                "last_win_date": last_win.strftime("%Y-%m-%d"),
                "days_since_last_win": days_since_last_win,
                "as_of_date": observation_end.strftime("%Y-%m-%d"),
                "interpretation": "Historical calendar-day gaps between draws with jackpot winners. These gaps do not estimate when another win will occur.",
            }

        return {
            "message": "At least two draws with winners are required for interval summaries"
        }

    def generate_winning_predictions(self, top_n: int = 5) -> List[Dict]:
        """
        Generate predictions based specifically on winning draw patterns.

        Args:
            top_n: Number of predictions to generate

        Returns:
            List of heuristic combinations based on draws with winners
        """
        self._validate_prediction_count(top_n)
        winning_draws = self.winning_draws

        if not winning_draws:
            return [
                {
                    **prediction,
                    "win_probability_score": prediction["confidence_score"],
                    "prediction_type": "Overall history (no draws with winners)",
                }
                for prediction in self.generate_top_predictions(top_n)
            ]

        # Analyze winning numbers with higher weight
        winning_numbers = [num for result in winning_draws for num in result["numbers"]]
        winning_freq = Counter(winning_numbers)

        # Calculate scores with emphasis on winning frequency
        max_freq = max(winning_freq.values()) if winning_freq else 1
        number_scores = {
            num: (freq / max_freq) * 1.5  # 1.5x weight for winning numbers
            for num, freq in winning_freq.items()
        }

        # Add other numbers with lower scores
        all_freq = self.number_frequency
        for num in range(1, self.max_number + 1):
            if num not in number_scores:
                number_scores[num] = (
                    all_freq.get(num, 0) / max(all_freq.values())
                ) * 0.5

        predictions = []
        seen_combinations = set()
        attempts = 0
        max_attempts = top_n * 100

        while len(predictions) < top_n and attempts < max_attempts:
            attempts += 1

            combo = self._sample_combination(number_scores, noise=0.2)

            if combo not in seen_combinations:
                seen_combinations.add(combo)
                score = self._calculate_winning_score(
                    combo, number_scores, winning_draws
                )

                predictions.append(
                    {
                        "numbers": list(combo),
                        "win_probability_score": round(score, 2),
                        "analysis": self._analyze_combination(combo),
                        "prediction_type": "Winner-subset history",
                    }
                )

        predictions.sort(key=lambda x: x["win_probability_score"], reverse=True)
        return predictions[:top_n]

    def _calculate_winning_score(
        self, combo: Tuple, number_scores: Dict, winning_draws: List[Dict]
    ) -> float:
        """Calculate score based on winning patterns."""
        # Base score from winning number frequencies
        base_score = sum(number_scores.get(num, 0) for num in combo) / len(combo)

        # Check if combo matches winning patterns
        winning_patterns = self._analyze_pattern_for_draws(winning_draws, "even_odd")
        combo_even = sum(1 for num in combo if num % 2 == 0)
        combo_pattern = f"{combo_even}E-{len(combo) - combo_even}O"

        pattern_bonus = (
            0.3 if combo_pattern == winning_patterns.get("most_common_pattern") else 0
        )

        # Range spread bonus
        spread = (max(combo) - min(combo)) / self.max_number
        spread_bonus = spread * 0.2

        total_score = (base_score * 0.7) + pattern_bonus + spread_bonus
        return min(total_score * 100, 100)

    def analyze_consecutive_draw_patterns(self) -> Dict:
        """
        Describe carryovers and chronological transitions between recorded draws.

        Returns:
            Dictionary with pattern analysis and predictions
        """
        if len(self.results) < 2:
            return {"message": "Insufficient data for consecutive draw analysis"}

        patterns = {
            "number_carryover": [],  # How many numbers repeat from previous draw
            "number_gaps": [],  # Gaps between draws
            "sum_differences": [],  # Difference in sums
            "pattern_transitions": defaultdict(int),  # Even/odd pattern changes
            "new_numbers_per_draw": [],  # How many new numbers appear
        }

        # Analyze consecutive draws
        chronological_draws = list(reversed(self.results))
        for current_draw, next_draw in zip(
            chronological_draws, chronological_draws[1:]
        ):
            current_nums = set(current_draw["numbers"])
            next_nums = set(next_draw["numbers"])

            # Count carryover (repeated numbers)
            carryover = len(current_nums & next_nums)
            patterns["number_carryover"].append(carryover)

            # Count new numbers
            new_numbers = len(next_nums - current_nums)
            patterns["new_numbers_per_draw"].append(new_numbers)

            # Sum difference
            sum_diff = abs(sum(next_draw["numbers"]) - sum(current_draw["numbers"]))
            patterns["sum_differences"].append(sum_diff)

            # Pattern transitions (even/odd)
            curr_even = sum(1 for n in current_nums if n % 2 == 0)
            next_even = sum(1 for n in next_nums if n % 2 == 0)
            curr_pattern = f"{curr_even}E-{len(current_nums) - curr_even}O"
            next_pattern = f"{next_even}E-{len(next_nums) - next_even}O"
            transition = f"{curr_pattern} → {next_pattern}"
            patterns["pattern_transitions"][transition] += 1

        # Calculate statistics
        analysis = {
            "average_carryover": round(float(np.mean(patterns["number_carryover"])), 2),
            "most_common_carryover": int(
                Counter(patterns["number_carryover"]).most_common(1)[0][0]
            ),
            "average_new_numbers": round(
                float(np.mean(patterns["new_numbers_per_draw"])), 2
            ),
            "average_sum_difference": round(
                float(np.mean(patterns["sum_differences"])), 2
            ),
            "most_common_pattern_transition": max(
                patterns["pattern_transitions"].items(), key=lambda x: x[1]
            )[0],
            "carryover_distribution": {
                int(k): int(v) for k, v in Counter(patterns["number_carryover"]).items()
            },
            "pattern_transitions": {
                k: int(v) for k, v in patterns["pattern_transitions"].items()
            },
        }

        latest_draw = self.results[0]  # Assuming most recent is first
        analysis["latest_draw"] = {
            "date": latest_draw["date"],
            "numbers": [
                int(n) for n in latest_draw["numbers"]
            ],  # Convert to native int
            "sum": int(sum(latest_draw["numbers"])),
        }

        return analysis

    def generate_pattern_based_prediction(self, top_n: int = 5) -> List[Dict]:
        """
        Generate predictions based on consecutive draw patterns.

        Args:
            top_n: Number of predictions to generate

        Returns:
            List of pattern-based predictions
        """
        self._validate_prediction_count(top_n)
        pattern_analysis = self.analyze_consecutive_draw_patterns()

        if "message" in pattern_analysis:
            return []

        latest_draw = self.results[0]
        latest_numbers = set(latest_draw["numbers"])

        number_freq = self.number_frequency

        # Expected carryover count
        expected_carryover = int(round(pattern_analysis["average_carryover"]))
        possible_combinations = comb(self.numbers_to_pick, expected_carryover) * comb(
            self.max_number - self.numbers_to_pick,
            self.numbers_to_pick - expected_carryover,
        )
        target_count = min(top_n, possible_combinations)
        if target_count < top_n:
            logger.warning(
                "Only %s unique combinations satisfy the exact %s-number carryover constraint",
                target_count,
                expected_carryover,
            )

        predictions = []
        seen_combinations = set()
        attempts = 0
        max_attempts = top_n * 200

        while len(predictions) < target_count and attempts < max_attempts:
            attempts += 1

            # Select numbers to carry over from latest draw
            if expected_carryover > 0 and expected_carryover <= len(latest_numbers):
                # Randomly select numbers to carry over
                carryover_nums = set(
                    self.rng.choice(
                        sorted(latest_numbers),
                        size=min(expected_carryover, len(latest_numbers)),
                        replace=False,
                    )
                )
            else:
                carryover_nums = set()

            # Fill remaining slots with new numbers based on frequency
            remaining_slots = self.numbers_to_pick - len(carryover_nums)

            available_numbers = [
                n for n in range(1, self.max_number + 1) if n not in latest_numbers
            ]
            available_freq = {n: number_freq.get(n, 0) for n in available_numbers}

            # Weighted selection for new numbers
            if available_numbers and remaining_slots > 0:
                weights = [
                    available_freq[n] + self.rng.random() * 50
                    for n in available_numbers
                ]
                probs = np.array(weights) / sum(weights)

                new_nums = set(
                    self.rng.choice(
                        available_numbers,
                        size=min(remaining_slots, len(available_numbers)),
                        replace=False,
                        p=probs,
                    )
                )
            else:
                new_nums = set()

            combo = carryover_nums | new_nums

            if len(combo) == self.numbers_to_pick:
                combo_tuple = tuple(sorted(combo))

                if combo_tuple not in seen_combinations:
                    seen_combinations.add(combo_tuple)

                    # Calculate score
                    score = self._calculate_pattern_score(
                        combo_tuple, latest_numbers, pattern_analysis
                    )

                    predictions.append(
                        {
                            "numbers": [
                                int(n) for n in combo_tuple
                            ],  # Convert to native int
                            "pattern_score": round(float(score), 2),
                            "carryover_count": int(len(combo & latest_numbers)),
                            "new_count": int(len(combo - latest_numbers)),
                            "analysis": self._analyze_combination(combo_tuple),
                            "prediction_type": "Pattern-Based",
                            "generation_note": (
                                f"Exact carryover constraint: {expected_carryover}; "
                                f"requested {top_n}, available {possible_combinations} unique combinations."
                            ),
                        }
                    )

        predictions.sort(key=lambda x: x["pattern_score"], reverse=True)
        if len(predictions) < target_count:
            raise DataValidationException(
                "Unable to generate the requested unique pattern combinations"
            )

        return predictions[:top_n]

    def _calculate_pattern_score(
        self, combo: Tuple, latest_numbers: set, pattern_analysis: Dict
    ) -> float:
        """Calculate score based on pattern analysis."""
        combo_set = set(combo)

        # Carryover score (how close to expected carryover)
        actual_carryover = len(combo_set & latest_numbers)
        expected_carryover = pattern_analysis["average_carryover"]
        carryover_diff = abs(actual_carryover - expected_carryover)
        carryover_score = max(0, 1 - (carryover_diff / self.numbers_to_pick))

        # Frequency score
        number_freq = self.number_frequency
        max_freq = max(number_freq.values())
        freq_score = sum(number_freq.get(num, 0) for num in combo) / (
            len(combo) * max_freq
        )

        # Pattern match score (even/odd balance)
        even_count = sum(1 for num in combo if num % 2 == 0)
        balance_score = 1.0 - abs(even_count - len(combo) / 2) / len(combo)

        # Combined score
        total_score = (
            (carryover_score * 0.4) + (freq_score * 0.3) + (balance_score * 0.3)
        )

        return min(total_score * 100, 100)

    def analyze_temporal_patterns(self) -> Dict:
        """
        Analyze patterns across different time dimensions: years, months, weeks, days.

        Returns:
            Dictionary containing temporal pattern analysis
        """
        if self._temporal_patterns is not None:
            return self._temporal_patterns

        temporal_analysis = {
            "by_year": {},
            "by_month": {},
            "by_week": {},
            "by_day_of_week": {},
            "year_over_year_trends": {},
            "monthly_trends": {},
            "weekly_patterns": {},
            "interpretation": "Rates are appearances per recorded draw. Calendar-month and ISO-week groups combine years. Observed coverage may be partial; rankings are descriptive, not significance tests or predictions.",
        }

        df = self.df.copy()
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month
        df["month_name"] = df["date"].dt.strftime("%B")
        df["week"] = df["date"].dt.isocalendar().week
        df["day_name"] = df["date"].dt.strftime("%A")

        # Year-based analysis
        for year in sorted(df["year"].unique()):
            year_data = df[df["year"] == year]
            year_numbers = [
                num for _, row in year_data.iterrows() for num in row["numbers"]
            ]
            year_freq = Counter({n: 0 for n in range(1, self.max_number + 1)})
            year_freq.update(year_numbers)

            temporal_analysis["by_year"][int(year)] = {
                "total_draws": len(year_data),
                "most_frequent": sorted(
                    year_freq.items(), key=lambda x: x[1], reverse=True
                )[:10],
                "hot_numbers": self._get_hot_numbers(year_freq, 10),
                "appearance_rates": {
                    n: frequency / len(year_data) for n, frequency in year_freq.items()
                },
                "expected_frequency": len(year_data)
                * self.numbers_to_pick
                / self.max_number,
                "coverage_start": year_data["date"].min().strftime("%Y-%m-%d"),
                "coverage_end": year_data["date"].max().strftime("%Y-%m-%d"),
                "average_per_number": np.mean(list(year_freq.values()))
                if year_freq
                else 0,
            }

        # Month-based analysis
        for month in range(1, 13):
            month_data = df[df["month"] == month]
            if len(month_data) == 0:
                continue

            month_numbers = [
                num for _, row in month_data.iterrows() for num in row["numbers"]
            ]
            month_freq = Counter(month_numbers)
            month_name = datetime(2000, month, 1).strftime("%B")

            temporal_analysis["by_month"][month_name] = {
                "month_number": month,
                "total_draws": len(month_data),
                "most_frequent": sorted(
                    month_freq.items(), key=lambda x: x[1], reverse=True
                )[:10],
                "hot_numbers": [num for num, _ in month_freq.most_common(6)],
                "appearance_rates": {
                    n: month_freq.get(n, 0) / len(month_data)
                    for n in range(1, self.max_number + 1)
                },
                "expected_frequency": len(month_data)
                * self.numbers_to_pick
                / self.max_number,
            }

        # Week-based analysis (week of year)
        week_groups = df.groupby("week")
        for week_num, week_data in week_groups:
            if not isinstance(week_num, (int, np.integer)):
                raise TypeError(
                    f"Expected an integer ISO week number, got {week_num!r}"
                )

            week_numbers = [
                num for _, row in week_data.iterrows() for num in row["numbers"]
            ]
            week_freq = Counter(week_numbers)

            temporal_analysis["by_week"][int(week_num)] = {
                "total_draws": len(week_data),
                "most_frequent": sorted(
                    week_freq.items(), key=lambda x: x[1], reverse=True
                )[:5],
                "hot_numbers": [num for num, _ in week_freq.most_common(6)],
                "appearance_rates": {
                    n: week_freq.get(n, 0) / len(week_data)
                    for n in range(1, self.max_number + 1)
                },
            }

        # Day of week analysis (enhanced)
        for day in self.DAYS_OF_WEEK:
            day_data = df[df["day_name"] == day]
            if len(day_data) == 0:
                continue

            day_numbers = [
                num for _, row in day_data.iterrows() for num in row["numbers"]
            ]
            day_freq = Counter(day_numbers)

            temporal_analysis["by_day_of_week"][day] = {
                "total_draws": len(day_data),
                "most_frequent": sorted(
                    day_freq.items(), key=lambda x: x[1], reverse=True
                )[:10],
                "hot_numbers": [num for num, _ in day_freq.most_common(6)],
                "appearance_rates": {
                    n: day_freq.get(n, 0) / len(day_data)
                    for n in range(1, self.max_number + 1)
                },
            }

        # Year-over-year trends (identify consistent numbers)
        years = sorted(df["year"].unique())
        if len(years) > 1:
            # Find numbers that appear frequently across all years
            number_consistency = defaultdict(list)

            for year in years:
                year_data = df[df["year"] == year]
                year_numbers = [
                    num for _, row in year_data.iterrows() for num in row["numbers"]
                ]
                year_freq = Counter(year_numbers)

                # Store frequency for each number per year
                for num in range(1, self.max_number + 1):
                    number_consistency[num].append(
                        year_freq.get(num, 0) / len(year_data)
                    )

            # Identify consistently high-performing numbers
            consistent_numbers = []
            for num, freqs in number_consistency.items():
                if len(freqs) >= 2:
                    avg_freq = np.mean(freqs)
                    std_freq = np.std(freqs)
                    if avg_freq > 0 and std_freq / avg_freq < 0.5:
                        consistent_numbers.append(
                            {
                                "number": num,
                                "average_frequency": round(
                                    self.number_frequency[num] / len(years), 2
                                ),
                                "average_appearance_rate": round(float(avg_freq), 6),
                                "consistency_score": round(
                                    float(1 - (std_freq / avg_freq)), 3
                                ),
                                "years_appeared": len([f for f in freqs if f > 0]),
                            }
                        )

            consistent_numbers.sort(key=lambda x: x["consistency_score"], reverse=True)

            temporal_analysis["year_over_year_trends"] = {
                "years_analyzed": [int(y) for y in years],
                "total_years": len(years),
                "consistent_performers": consistent_numbers[:15],
                "distinct_high_performers": self._identify_distinct_performers(
                    df, years
                ),
            }

        # Monthly trends
        temporal_analysis["monthly_trends"] = self._analyze_monthly_trends(df)

        # Weekly patterns
        temporal_analysis["weekly_patterns"] = self._analyze_weekly_patterns(df)

        self._temporal_patterns = temporal_analysis
        return temporal_analysis

    def _identify_distinct_performers(
        self, df: pd.DataFrame, years: list
    ) -> List[Dict]:
        """Identify numbers that perform exceptionally well in specific years."""
        distinct_performers = []

        for year in years:
            year_data = df[df["year"] == year]
            year_numbers = [
                num for _, row in year_data.iterrows() for num in row["numbers"]
            ]
            year_freq = Counter(year_numbers)

            top_5 = year_freq.most_common(5)
            other_years_data = df[df["year"] != year]
            other_numbers = [
                n for _, row in other_years_data.iterrows() for n in row["numbers"]
            ]
            other_freq = Counter(other_numbers)

            for num, freq in top_5:
                rate = freq / len(year_data)
                other_rate = other_freq.get(num, 0) / len(other_years_data)
                if rate > other_rate * 1.5:
                    distinct_performers.append(
                        {
                            "number": num,
                            "year": int(year),
                            "frequency": freq,
                            "total_draws": len(year_data),
                            "appearance_rate": round(rate, 6),
                            "other_years_appearance_rate": round(other_rate, 6),
                            "improvement_over_average": round(
                                (rate / other_rate - 1) * 100, 1
                            )
                            if other_rate
                            else None,
                            "rate_difference_percentage_points": round(
                                (rate - other_rate) * 100, 2
                            ),
                        }
                    )

        return distinct_performers[:10]

    def _analyze_monthly_trends(self, df: pd.DataFrame) -> Dict:
        """Analyze how numbers trend across months."""
        monthly_number_freq = defaultdict(lambda: defaultdict(int))

        for _, row in df.iterrows():
            month = str(row["month_name"])
            for num in row["numbers"]:
                monthly_number_freq[month][num] += 1

        # Find numbers with strong monthly preferences
        monthly_favorites = {}
        for month, freq_dict in monthly_number_freq.items():
            if freq_dict:
                top_numbers = sorted(
                    freq_dict.items(), key=lambda x: x[1], reverse=True
                )[:5]
                monthly_favorites[month] = [
                    {
                        "number": num,
                        "frequency": freq,
                        "appearance_rate": freq
                        / int((df["month_name"] == month).sum()),
                    }
                    for num, freq in top_numbers
                ]

        return {
            "monthly_favorites": monthly_favorites,
            "total_months_analyzed": len(monthly_number_freq),
        }

    def _analyze_weekly_patterns(self, df: pd.DataFrame) -> Dict:
        """Analyze patterns within weeks."""
        # Analyze first vs second half of month
        df_copy = df.copy()
        df_copy["day_of_month"] = df_copy["date"].dt.day

        first_half = df_copy[df_copy["day_of_month"] <= 15]
        second_half = df_copy[df_copy["day_of_month"] > 15]

        first_half_numbers = [
            num for _, row in first_half.iterrows() for num in row["numbers"]
        ]
        second_half_numbers = [
            num for _, row in second_half.iterrows() for num in row["numbers"]
        ]

        first_freq = Counter(first_half_numbers)
        second_freq = Counter(second_half_numbers)

        return {
            "first_half_month": {
                "total_draws": len(first_half),
                "top_numbers": [num for num, _ in first_freq.most_common(10)],
                "appearance_rates": {
                    n: first_freq.get(n, 0) / len(first_half)
                    for n in range(1, self.max_number + 1)
                }
                if len(first_half)
                else {},
            },
            "second_half_month": {
                "total_draws": len(second_half),
                "top_numbers": [num for num, _ in second_freq.most_common(10)],
                "appearance_rates": {
                    n: second_freq.get(n, 0) / len(second_half)
                    for n in range(1, self.max_number + 1)
                }
                if len(second_half)
                else {},
            },
        }

    def get_historical_observations(self) -> Dict:
        """
        Generate observations from historical data analysis.

        Returns:
            Dictionary containing key observations about the lottery data
        """
        all_numbers = [num for result in self.results for num in result["numbers"]]
        number_freq = Counter(all_numbers)

        observations = {
            "highly_frequent_numbers": [],
            "common_repeating_patterns": [],
            "year_to_year_insights": [],
            "consistency_insights": [],
            "temporal_insights": [],
        }

        # Highly frequent numbers (top 15)
        top_frequent = sorted(number_freq.items(), key=lambda x: x[1], reverse=True)[
            :15
        ]
        total_draws = len(self.results)

        for num, freq in top_frequent:
            appearance_rate = (freq / total_draws) * 100
            observations["highly_frequent_numbers"].append(
                {
                    "number": num,
                    "frequency": freq,
                    "appearance_rate": round(appearance_rate, 2),
                    "observation": f"Number {num} appears in {appearance_rate:.1f}% of all draws",
                }
            )

        # Common repeating patterns
        # Check for numbers that appear in consecutive draws
        consecutive_appearances = defaultdict(int)
        for i in range(len(self.results) - 1):
            current_set = set(self.results[i]["numbers"])
            next_set = set(self.results[i + 1]["numbers"])
            repeated = current_set & next_set

            for num in repeated:
                consecutive_appearances[num] += 1

        if consecutive_appearances:
            observations["common_repeating_patterns"] = [
                {
                    "number": num,
                    "consecutive_occurrences": count,
                    "observation": f"Number {num} repeated across {count} adjacent draw pairs (not a streak length)",
                }
                for num, count in sorted(
                    consecutive_appearances.items(), key=lambda x: x[1], reverse=True
                )[:10]
            ]

        # Year-to-year insights
        temporal_analysis = self.analyze_temporal_patterns()
        if "year_over_year_trends" in temporal_analysis:
            yoy_trends = temporal_analysis["year_over_year_trends"]

            if "consistent_performers" in yoy_trends:
                observations["year_to_year_insights"] = [
                    {
                        "number": perf["number"],
                        "consistency_score": perf["consistency_score"],
                        "years_appeared": perf["years_appeared"],
                        "observation": f"Number {perf['number']} is highly consistent across {perf['years_appeared']} years",
                    }
                    for perf in yoy_trends["consistent_performers"][:10]
                ]

            if "distinct_high_performers" in yoy_trends:
                observations["consistency_insights"] = [
                    {
                        "number": perf["number"],
                        "year": perf["year"],
                        "improvement": perf["improvement_over_average"],
                        "observation": f"Number {perf['number']} had an appearance rate {perf['rate_difference_percentage_points']:.2f} percentage points above other recorded years in {perf['year']}",
                    }
                    for perf in yoy_trends["distinct_high_performers"]
                ]

        # Temporal insights
        if "by_month" in temporal_analysis:
            monthly_insights = []
            for month, data in temporal_analysis["by_month"].items():
                if data["hot_numbers"]:
                    monthly_insights.append(
                        {
                            "month": month,
                            "hot_numbers": data["hot_numbers"][:3],
                            "observation": f"In {month}, numbers {', '.join(map(str, data['hot_numbers'][:3]))} appear most frequently",
                        }
                    )

            observations["temporal_insights"] = monthly_insights

        return observations

    def generate_ultimate_predictions(self, top_n: int = 5) -> List[Dict]:
        """
        Generate ultimate predictions combining all analysis methods.
        Acknowledges randomness while using historical patterns.

        Args:
            top_n: Number of predictions to generate

        Returns:
            List of comprehensive predictions with detailed analysis
        """
        self._validate_prediction_count(top_n)
        number_freq = self.number_frequency
        temporal_patterns = self.analyze_temporal_patterns()
        historical_obs = self.get_historical_observations()

        number_scores = defaultdict(float)

        # 1. Frequency score (30% weight)
        max_freq = max(number_freq.values()) if number_freq else 1
        for num, freq in number_freq.items():
            number_scores[num] += (freq / max_freq) * 0.30

        # 2. Temporal consistency score (25% weight)
        if "year_over_year_trends" in temporal_patterns:
            consistent_performers = temporal_patterns["year_over_year_trends"].get(
                "consistent_performers", []
            )
            for perf in consistent_performers:
                num = perf["number"]
                number_scores[num] += perf["consistency_score"] * 0.25

        # 3. Recent performance score (20% weight)
        recent_draws = self.results[: min(50, len(self.results))]
        recent_numbers = [num for result in recent_draws for num in result["numbers"]]
        recent_freq = Counter(recent_numbers)
        max_recent = max(recent_freq.values()) if recent_freq else 1

        for num, freq in recent_freq.items():
            number_scores[num] += (freq / max_recent) * 0.20

        # 4. Winning draw performance (15% weight)
        winning_draws = self.winning_draws

        if winning_draws:
            winning_numbers = [
                num for result in winning_draws for num in result["numbers"]
            ]
            winning_freq = Counter(winning_numbers)
            max_winning = max(winning_freq.values()) if winning_freq else 1

            for num, freq in winning_freq.items():
                number_scores[num] += (freq / max_winning) * 0.15

        # Adjacent-repeat counts are descriptive, not evidence of future repeats.
        repeating_numbers = historical_obs.get("common_repeating_patterns", [])
        max_repeats = max(
            (item["consecutive_occurrences"] for item in repeating_numbers), default=1
        )
        for item in repeating_numbers:
            num = item["number"]
            number_scores[num] += (item["consecutive_occurrences"] / max_repeats) * 0.10

        # Normalize scores
        max_score = max(number_scores.values()) if number_scores else 1
        for num in number_scores:
            number_scores[num] = number_scores[num] / max_score

        # Ensure all numbers have a score (for randomness)
        for num in range(1, self.max_number + 1):
            if not number_scores[num]:
                number_scores[num] = 0.05

        predictions = []
        seen_combinations = set()
        attempts = 0
        max_attempts = top_n * 500

        while len(predictions) < top_n and attempts < max_attempts:
            attempts += 1

            combo = self._sample_combination(number_scores, noise=0.4)

            if combo not in seen_combinations:
                seen_combinations.add(combo)

                components = self._ultimate_scoring_components(
                    combo, number_scores, temporal_patterns
                )
                confidence = min(sum(components.values()), 100)

                analysis = self._analyze_combination(combo)
                analysis["randomness_acknowledgment"] = (
                    "These historical-pattern scores are not winning probabilities. "
                    "Lottery draws are random; these combinations do not improve winning odds."
                )

                predictions.append(
                    {
                        "numbers": list(combo),
                        "ultimate_confidence_score": round(float(confidence), 2),
                        "analysis": analysis,
                        "prediction_type": "Combined historical analysis",
                        "scoring_components": {
                            name: round(float(points), 2)
                            for name, points in components.items()
                        },
                    }
                )

        predictions.sort(key=lambda x: x["ultimate_confidence_score"], reverse=True)

        return predictions[:top_n]

    def _calculate_ultimate_score(
        self,
        combo: Tuple,
        number_scores: Dict,
        temporal_patterns: Dict,
    ) -> float:
        """Sum historical-pattern components, not calibrated probabilities."""
        return min(
            sum(
                self._ultimate_scoring_components(
                    combo, number_scores, temporal_patterns
                ).values()
            ),
            100,
        )

    def _ultimate_scoring_components(
        self, combo: Tuple, number_scores: Dict, temporal_patterns: Dict
    ) -> Dict[str, float]:
        return {
            "frequency_score": sum(number_scores.get(num, 0) for num in combo)
            / len(combo)
            * 30,
            "pattern_match": self._pattern_match_score(
                combo,
                self._get_recent_pattern_preference("even_odd"),
                self._get_recent_pattern_preference("high_low"),
            )
            * 25,
            "temporal_consistency": self._temporal_consistency_score(
                combo, temporal_patterns
            )
            * 25,
            "balance_score": self._balance_score(combo) * 20,
        }

    def _pattern_match_score(
        self, combo: Tuple, recent_even_odd: str, recent_high_low: str
    ) -> float:
        """Score based on pattern matching."""
        score = 0.0

        # Even/odd match
        even_count = sum(1 for num in combo if num % 2 == 0)
        combo_pattern = f"{even_count}E-{len(combo) - even_count}O"
        if combo_pattern == recent_even_odd:
            score += 0.5

        # High/low match
        mid_point = self.max_number // 2
        low_count = sum(1 for num in combo if num <= mid_point)
        combo_hl_pattern = f"{low_count}L-{len(combo) - low_count}H"
        if combo_hl_pattern == recent_high_low:
            score += 0.5

        return score

    def _temporal_consistency_score(
        self, combo: Tuple, temporal_patterns: Dict
    ) -> float:
        """Score based on temporal consistency."""
        if not temporal_patterns.get("year_over_year_trends"):
            return 0.5

        consistent_performers = temporal_patterns["year_over_year_trends"].get(
            "consistent_performers", []
        )
        consistent_numbers = {p["number"] for p in consistent_performers}

        matches = len(set(combo) & consistent_numbers)
        return matches / len(combo)

    def _balance_score(self, combo: Tuple) -> float:
        """Score based on number balance and distribution."""
        # Even/odd balance
        even_count = sum(1 for num in combo if num % 2 == 0)
        even_odd_balance = 1.0 - abs(even_count - len(combo) / 2) / len(combo)

        # Range spread
        spread = (max(combo) - min(combo)) / self.max_number

        # Sum within expected range
        expected_sum = ((self.max_number + 1) / 2) * len(combo)
        actual_sum = sum(combo)
        sum_diff = abs(actual_sum - expected_sum) / expected_sum
        sum_score = max(0, 1 - sum_diff)

        return (even_odd_balance * 0.4) + (spread * 0.3) + (sum_score * 0.3)

    def get_chart_data(self) -> Dict:
        """
        Prepare data for charts and visualizations.

        Returns:
            Dictionary containing data formatted for charts
        """
        all_numbers = [num for result in self.results for num in result["numbers"]]
        number_freq = Counter(all_numbers)

        # Frequency distribution
        freq_data = {
            "labels": [str(i) for i in range(1, self.max_number + 1)],
            "values": [number_freq.get(i, 0) for i in range(1, self.max_number + 1)],
        }

        # Day of week distribution
        day_counts = Counter([r["day_of_week"] for r in self.results])
        day_data = {
            "labels": self.DAYS_OF_WEEK,
            "values": [day_counts.get(day, 0) for day in self.DAYS_OF_WEEK],
        }

        # Even/Odd distribution
        even_odd = self._analyze_even_odd()
        even_odd_data = {
            "labels": list(even_odd["patterns"].keys()),
            "values": list(even_odd["patterns"].values()),
        }

        # Sum distribution
        sums = [sum(result["numbers"]) for result in self.results]
        sum_hist, sum_bins = np.histogram(sums, bins=20)
        sum_data = {
            "labels": [
                f"{int(sum_bins[i])}-{int(sum_bins[i + 1])}"
                for i in range(len(sum_bins) - 1)
            ],
            "values": sum_hist.tolist(),
        }

        # Heatmap data (number frequency matrix)
        heatmap_data = self._generate_heatmap_data()

        # Trend graphs (temporal trends)
        trend_data = self._generate_trend_data()

        return {
            "number_frequency": freq_data,
            "day_distribution": day_data,
            "even_odd_patterns": even_odd_data,
            "sum_distribution": sum_data,
            "heatmap": heatmap_data,
            "trends": trend_data,
        }

    def _generate_heatmap_data(self) -> Dict:
        """Generate heatmap data for number frequency visualization."""

        if self.df.empty:
            return {}

        df = self.df.copy()
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month

        years = sorted(df["year"].unique())
        months = list(range(1, 13))

        # Heatmap 1: Number frequency by month (all years combined)
        month_number_freq = np.zeros((self.max_number, 12))

        for month in months:
            month_data = df[df["month"] == month]
            month_numbers = [
                num for _, row in month_data.iterrows() for num in row["numbers"]
            ]
            month_freq = Counter(month_numbers)

            for num in range(1, self.max_number + 1):
                month_number_freq[num - 1][month - 1] = month_freq.get(num, 0)

        # Heatmap 2: Number frequency by year
        year_number_freq = np.zeros((self.max_number, len(years)))

        for idx, year in enumerate(years):
            year_data = df[df["year"] == year]
            year_numbers = [
                num for _, row in year_data.iterrows() for num in row["numbers"]
            ]
            year_freq = Counter(year_numbers)

            for num in range(1, self.max_number + 1):
                year_number_freq[num - 1][idx] = year_freq.get(num, 0)

        # Heatmap 3: Day of week frequency
        day_number_freq = np.zeros((self.max_number, 7))

        for idx, day in enumerate(self.DAYS_OF_WEEK):
            day_data = [r for r in self.results if r["day_of_week"] == day]
            day_numbers = [num for result in day_data for num in result["numbers"]]
            day_freq = Counter(day_numbers)

            for num in range(1, self.max_number + 1):
                day_number_freq[num - 1][idx] = day_freq.get(num, 0)

        month_counts = [int((df["month"] == month).sum()) for month in months]
        year_counts = [int((df["year"] == year).sum()) for year in years]
        day_counts = Counter(result["day_of_week"] for result in self.results)
        weekday_counts = [day_counts.get(day, 0) for day in self.DAYS_OF_WEEK]

        def rates(matrix: np.ndarray, sample_sizes: list[int]) -> list:
            return [
                [
                    float(value) / count * 100 if count else None
                    for value, count in zip(row, sample_sizes)
                ]
                for row in matrix
            ]

        return {
            "by_month": {
                "data": month_number_freq.tolist(),
                "appearance_rates_percent": rates(month_number_freq, month_counts),
                "sample_sizes": month_counts,
                "rate_title": "Number Appearance Rate by Month (%)",
                "x_labels": [
                    "Jan",
                    "Feb",
                    "Mar",
                    "Apr",
                    "May",
                    "Jun",
                    "Jul",
                    "Aug",
                    "Sep",
                    "Oct",
                    "Nov",
                    "Dec",
                ],
                "y_labels": [str(i) for i in range(1, self.max_number + 1)],
                "title": "Number Frequency by Month",
            },
            "by_year": {
                "data": year_number_freq.tolist(),
                "appearance_rates_percent": rates(year_number_freq, year_counts),
                "sample_sizes": year_counts,
                "rate_title": "Number Appearance Rate by Year (%)",
                "x_labels": [str(int(y)) for y in years],
                "y_labels": [str(i) for i in range(1, self.max_number + 1)],
                "title": "Number Frequency by Year",
            },
            "by_day": {
                "data": day_number_freq.tolist(),
                "appearance_rates_percent": rates(day_number_freq, weekday_counts),
                "sample_sizes": weekday_counts,
                "rate_title": "Number Appearance Rate by Day of Week (%)",
                "x_labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                "y_labels": [str(i) for i in range(1, self.max_number + 1)],
                "title": "Number Frequency by Day of Week",
            },
        }

    def _generate_trend_data(self) -> Dict:
        """Generate trend graph data showing temporal patterns."""
        if self.df.empty:
            return {}

        df = self.df.copy()
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month
        df["year_month"] = df["date"].dt.to_period("M")

        # Trend 1: Top 10 numbers frequency over time
        top_numbers = [
            num
            for num, _ in Counter(
                [num for result in self.results for num in result["numbers"]]
            ).most_common(10)
        ]

        monthly_trends = defaultdict(lambda: defaultdict(int))
        for _, row in df.iterrows():
            period = str(row["year_month"])
            for num in row["numbers"]:
                if num in top_numbers:
                    monthly_trends[period][num] += 1

        periods = sorted(str(period) for period in df["year_month"].unique())
        period_counts = {
            period: int((df["year_month"] == period).sum()) for period in periods
        }

        trend_lines = {}
        for num in top_numbers:
            trend_lines[str(num)] = [
                monthly_trends[period].get(num, 0) for period in periods
            ]

        # Trend 2: Average draw sum over time
        sum_trend = []
        for period in periods:
            period_data = df[df["year_month"] == period]
            period_sums = [sum(row["numbers"]) for _, row in period_data.iterrows()]
            sum_trend.append(np.mean(period_sums) if period_sums else 0)

        # Trend 3: Even/odd ratio over time
        even_ratio_trend = []
        for period in periods:
            period_data = df[df["year_month"] == period]
            even_counts = []
            for _, row in period_data.iterrows():
                even_count = sum(1 for num in row["numbers"] if num % 2 == 0)
                even_counts.append(even_count / len(row["numbers"]))

            even_ratio_trend.append(np.mean(even_counts) if even_counts else 0)

        # Trend 4: Consistency score over time (top numbers)
        consistency_trend = []
        window_size = 10  # 10-draw window

        chronological_draws = list(reversed(self.results))
        for i in range(len(chronological_draws) - window_size + 1):
            window = chronological_draws[i : i + window_size]
            window_freq = self._frequency(window)

            # Coefficient of variation
            freqs = list(window_freq.values())
            if freqs and np.mean(freqs) > 0:
                cv = np.std(freqs) / np.mean(freqs)
                consistency_trend.append(
                    1 - min(cv, 1)
                )  # Lower CV = higher consistency
            else:
                consistency_trend.append(0)

        return {
            "top_numbers_over_time": {
                "labels": periods,
                "datasets": [
                    {
                        "label": f"Number {num}",
                        "data": [
                            monthly_trends[period].get(num, 0)
                            / period_counts[period]
                            * 100
                            for period in periods
                        ],
                    }
                    for num in top_numbers
                ],
                "count_datasets": [
                    {"label": f"Number {num}", "data": trend_lines[str(num)]}
                    for num in top_numbers
                ],
                "sample_sizes": [period_counts[period] for period in periods],
                "title": "Top 10 Recorded Numbers: Appearance Rate Over Time (%)",
                "interpretation": "Top numbers selected from this complete historical sample, not an out-of-sample forecast.",
            },
            "average_sum_trend": {
                "labels": periods,
                "data": sum_trend,
                "title": "Average Draw Sum Over Time",
            },
            "even_odd_ratio_trend": {
                "labels": periods,
                "data": even_ratio_trend,
                "title": "Even Number Ratio Over Time",
            },
            "consistency_trend": {
                "labels": [
                    draw["date"] for draw in chronological_draws[window_size - 1 :]
                ],
                "data": consistency_trend,
                "title": "Number Distribution Consistency (Rolling Window)",
            },
        }
