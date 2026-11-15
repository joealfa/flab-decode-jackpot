"""Reproducible, retrospective walk-forward checks against random tickets."""

import hashlib
import json
import platform
from collections import Counter
from math import comb
from typing import Any

import numpy as np

from app.exceptions import DataValidationException, InsufficientDataException
from app.modules.analyzer import LotteryAnalyzer
from app.serialization import convert_to_serializable

ALGORITHMS = (
    ("top", "generate_top_predictions"),
    ("winning", "generate_winning_predictions"),
    ("pattern", "generate_pattern_based_prediction"),
    ("ultimate", "generate_ultimate_predictions"),
)


def _fingerprint(data: Any) -> str:
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _mean_interval(
    values: np.ndarray, rng: np.random.Generator, tail: float
) -> list[float]:
    # Resample whole draws, not correlated tickets facing the same outcome.
    resampled = rng.choice(values, size=(2000, len(values)), replace=True).mean(axis=1)
    return [float(value) for value in np.quantile(resampled, [tail, 1 - tail])]


def evaluate_walk_forward(
    data: dict,
    *,
    evaluation_draws: int = 50,
    min_training_draws: int = 50,
    tickets: int = 5,
    seed: int = 42,
) -> dict:
    """Evaluate four fixed heuristics on the latest held-out draws of one game."""
    for name, value, minimum, maximum in (
        ("evaluation_draws", evaluation_draws, 2, None),
        ("min_training_draws", min_training_draws, 2, None),
        ("tickets", tickets, 1, 100),
        ("seed", seed, 0, None),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise DataValidationException(f"{name} must be an integer >= {minimum}")
        if maximum is not None and value > maximum:
            raise DataValidationException(f"{name} must be <= {maximum}")

    normalized = LotteryAnalyzer(data)
    chronological = list(reversed(normalized.results))
    start = len(chronological) - evaluation_draws
    if start < min_training_draws:
        raise InsufficientDataException(
            f"Need at least {min_training_draws + evaluation_draws} unique draws "
            f"for this evaluation; found {len(chronological)}"
        )

    folds = []
    scores: dict[str, list[float]] = {name: [] for name, _ in ALGORITHMS}
    scores["random"] = []
    histograms: dict[str, Counter] = {name: Counter() for name in scores}
    for index in range(start, len(chronological)):
        training = chronological[:index]
        analyzer = LotteryAnalyzer(
            {"game_type": normalized.game_type, "results": training}
        )
        predictions = {}
        for algorithm_index, (name, method_name) in enumerate(ALGORITHMS):
            analyzer.rng = np.random.default_rng(
                np.random.SeedSequence([seed, index, algorithm_index])
            )
            generated = getattr(analyzer, method_name)(top_n=tickets)
            if len(generated) != tickets:
                raise InsufficientDataException(
                    f"{name} generated {len(generated)} of {tickets} unique tickets "
                    f"for {chronological[index]['date']}; equal-ticket evaluation is not possible"
                )
            predictions[name] = [prediction["numbers"] for prediction in generated]

        random_rng = np.random.default_rng(
            np.random.SeedSequence([seed, index, len(ALGORITHMS)])
        )
        random_tickets: set[tuple[int, ...]] = set()
        while len(random_tickets) < tickets:
            numbers = (
                random_rng.choice(
                    normalized.max_number,
                    size=normalized.numbers_to_pick,
                    replace=False,
                )
                + 1
            )
            random_tickets.add(tuple(sorted(int(number) for number in numbers)))
        predictions["random"] = [list(numbers) for numbers in sorted(random_tickets)]

        # All ticket sets are frozen before revealing this fold's outcome.
        target = chronological[index]
        actual_numbers = set(target["numbers"])
        comparisons = {}
        for name, generated_tickets in predictions.items():
            matches = [
                len(set(numbers) & actual_numbers) for numbers in generated_tickets
            ]
            histograms[name].update(matches)
            scores[name].append(float(np.mean(matches)))
            comparisons[name] = {"tickets": generated_tickets, "matches": matches}
        folds.append(
            {
                "target_date": target["date"],
                "actual_numbers": target["numbers"],
                "training_draws": len(training),
                "training_end": training[-1]["date"],
                "training_sha256": _fingerprint(training),
                "comparisons": comparisons,
            }
        )

    maximum = normalized.max_number
    total_combinations = comb(maximum, normalized.numbers_to_pick)
    match_probabilities = {
        matches: comb(6, matches) * comb(maximum - 6, 6 - matches) / total_combinations
        for matches in range(7)
    }
    random_means = np.array(scores["random"])
    summary = {}
    uncertainty_rng = np.random.default_rng(
        np.random.SeedSequence([seed, len(chronological), 99])
    )
    for name, means in scores.items():
        values = np.array(means)
        metrics = {
            "total_tickets": evaluation_draws * tickets,
            "mean_matches_per_ticket": float(values.mean()),
            "mean_matches_95_interval": _mean_interval(values, uncertainty_rng, 0.025),
            "match_distribution": {
                matches: histograms[name].get(matches, 0) for matches in range(7)
            },
        }
        if name != "random":
            differences = values - random_means
            metrics["mean_difference_vs_random"] = float(differences.mean())
            metrics["difference_familywise_95_interval"] = _mean_interval(
                differences, uncertainty_rng, 0.05 / (2 * len(ALGORITHMS))
            )
        summary[name] = metrics

    return convert_to_serializable(
        {
            "evaluation_version": 1,
            "analysis_version": normalized.ANALYSIS_VERSION,
            "method": "retrospective_walk_forward",
            "game_type": normalized.game_type,
            "seed": seed,
            "numpy_version": np.__version__,
            "python_version": platform.python_version(),
            "random_generator": "PCG64",
            "dataset_sha256": _fingerprint(normalized.results),
            "data_quality": normalized.input_quality,
            "parameters": {
                "evaluation_draws": evaluation_draws,
                "min_training_draws": min_training_draws,
                "tickets_per_algorithm_per_draw": tickets,
            },
            "fair_draw_baseline": {
                "expected_matches_per_ticket": 36 / maximum,
                "jackpot_combinations": total_combinations,
                "match_probabilities": match_probabilities,
                "expected_match_counts": {
                    matches: probability * evaluation_draws * tickets
                    for matches, probability in match_probabilities.items()
                },
            },
            "uncertainty": {
                "method": "paired draw-level percentile bootstrap",
                "resamples": 2000,
                "comparison_adjustment": "Bonferroni across four heuristic-versus-random comparisons",
                "limitations": (
                    "Intervals are approximate and assume draws can be resampled independently. "
                    "Small samples and overlapping expanding training histories limit inference."
                ),
            },
            "interpretation": (
                "Historical simulation, not proof of predictions committed before actual draws. "
                "Fixed versioned heuristic weights; no tuning is performed on these outcomes. "
                "If results guide weight changes, use a separate untouched evaluation period. "
                "Observed differences do not establish improved winning odds."
            ),
            "summary": summary,
            "folds": folds,
        }
    )
