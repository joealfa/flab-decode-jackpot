"""Regression checks for validated historical statistics and heuristic sampling."""

from copy import deepcopy
from datetime import datetime, timedelta

import numpy as np
import pytest

from app.exceptions import (
    BadRequestException,
    DataValidationException,
    InsufficientDataException,
    InvalidNumbersException,
)
from app.modules.analyzer import LotteryAnalyzer
from app.services.analysis import build_analysis_report
from app.validators import normalize_winner_count


def draw(date: datetime, numbers: list[int], winners="0") -> dict:
    return {
        "date": date.strftime("%m/%d/%Y"),
        "day_of_week": date.strftime("%A"),
        "numbers": numbers,
        "winners": winners,
        "jackpot": "N/A",
    }


def dataset(count: int = 60, maximum: int = 42) -> dict:
    rng = np.random.default_rng(1234)
    names = {
        42: "Lotto",
        45: "Mega Lotto",
        49: "Super Lotto",
        55: "Grand Lotto",
        58: "Ultra Lotto",
    }
    return {
        "game_type": f"{names[maximum]} 6/{maximum}",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "results": [
            draw(
                datetime(2026, 1, 1) + timedelta(days=index),
                sorted(int(n) for n in rng.choice(maximum, size=6, replace=False) + 1),
                "1" if index % 7 == 0 else "0",
            )
            for index in range(count)
        ],
    }


def test_normalization_deduplicates_without_mutating_source(caplog):
    data = dataset(3)
    data["results"].append(deepcopy(data["results"][0]))
    data["results"][1]["day_of_week"] = "Unknown"
    original = deepcopy(data)
    analyzer = LotteryAnalyzer(data)
    assert data == original
    assert len(analyzer.results) == 3
    assert analyzer.input_quality["duplicate_records_removed"] == 1
    assert analyzer.input_quality["weekday_labels_corrected"] == 1
    assert analyzer.data["end_date"] == "2026-01-03"
    assert "Normalized" in caplog.text
    assert sum(analyzer.number_frequency.values()) == 18


def test_conflicting_duplicates_are_rejected():
    data = dataset(3)
    duplicate = deepcopy(data["results"][0])
    duplicate["numbers"] = [1, 2, 3, 4, 5, 6]
    data["results"].append(duplicate)
    with pytest.raises(DataValidationException, match="Conflicting duplicate"):
        LotteryAnalyzer(data)


@pytest.mark.parametrize(
    "numbers", [[1, 1, 2, 3, 4, 5], [1, 2, 3, 4, 5, 43], [True, 2, 3, 4, 5, 6], [1, 2]]
)
def test_invalid_historical_numbers_are_rejected(numbers):
    data = dataset(1)
    data["results"][0]["numbers"] = numbers
    with pytest.raises(InvalidNumbersException):
        LotteryAnalyzer(data)


def test_empty_and_invalid_dates_are_explicit_errors():
    with pytest.raises(InsufficientDataException):
        LotteryAnalyzer(dataset(0))
    data = dataset(1)
    data["results"][0]["date"] = "not-a-date"
    with pytest.raises(DataValidationException, match="Invalid draw date"):
        LotteryAnalyzer(data)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0 ", 0),
        ("0 winners", 0),
        ("No winner", 0),
        ("n/a", None),
        (None, None),
        ("1 winner", 1),
        ("433", 433),
        (0, 0),
    ],
)
def test_winner_counts_are_normalized(raw, expected):
    assert normalize_winner_count(raw) == expected
    data = dataset(1)
    data["results"][0]["winners"] = raw
    analyzer = LotteryAnalyzer(data)
    assert analyzer.get_winner_analysis()["total_winning_draws"] == int(bool(expected))


@pytest.mark.parametrize("raw", [True, -1, 1.5, "maybe"])
def test_invalid_winner_counts_are_rejected(raw):
    with pytest.raises(BadRequestException, match="Winner count"):
        normalize_winner_count(raw)


def test_zero_frequency_numbers_and_wilson_intervals():
    data = dataset(1)
    data["results"][0]["numbers"] = [1, 2, 3, 4, 5, 6]
    stats = LotteryAnalyzer(data).get_overall_statistics()
    assert len(stats["number_frequency"]) == 42
    assert stats["average_frequency"] == pytest.approx(6 / 42)
    assert stats["cold_numbers"] == list(range(7, 17))
    context = stats["frequency_context"]
    assert context["expected_frequency"] == pytest.approx(6 / 42)
    assert context["number_statistics"][7]["wilson_95_interval"] == pytest.approx(
        [0, 0.793451]
    )
    assert context["number_statistics"][1]["wilson_95_interval"] == pytest.approx(
        [0.206549, 1]
    )
    assert sum(
        stats["even_odd_analysis"]["expected_pattern_probabilities"].values()
    ) == pytest.approx(1)
    assert stats["sum_analysis"]["expected_average_sum"] == 129


def test_recent_preferences_and_transitions_use_correct_chronology():
    data = dataset(40)
    for index, result in enumerate(data["results"]):
        result["numbers"] = [1, 3, 5, 7, 9, 11] if index < 20 else [1, 2, 3, 4, 5, 6]
    analyzer = LotteryAnalyzer(data)
    assert analyzer._get_recent_pattern_preference("even_odd") == "3E-3O"
    data["results"] = [
        draw(datetime(2026, 1, 1), [1, 3, 5, 7, 9, 11]),
        draw(datetime(2026, 1, 2), [2, 4, 6, 8, 10, 12]),
    ]
    transitions = LotteryAnalyzer(data).analyze_consecutive_draw_patterns()[
        "pattern_transitions"
    ]
    assert transitions == {"0E-6O \u2192 6E-0O": 1}


def test_pattern_sampling_enforces_exact_carryover():
    data = dataset(2)
    data["results"][0]["numbers"] = [1, 3, 5, 7, 9, 11]
    data["results"][1]["numbers"] = [2, 4, 6, 8, 10, 12]
    predictions = LotteryAnalyzer(
        data, rng=np.random.default_rng(123)
    ).generate_pattern_based_prediction(20)
    assert len(predictions) == 20
    assert all(prediction["carryover_count"] == 0 for prediction in predictions)
    assert len({tuple(prediction["numbers"]) for prediction in predictions}) == 20


def test_temporal_rates_do_not_confuse_exposure_with_improvement():
    data = dataset(0)
    data["results"] = [
        draw(datetime(year, 1, 1) + timedelta(days=index), [1, 2, 3, 4, 5, 6])
        for year, count in [(2025, 10), (2026, 40)]
        for index in range(count)
    ]
    analyzer = LotteryAnalyzer(data)
    temporal = analyzer.analyze_temporal_patterns()
    assert temporal["year_over_year_trends"]["distinct_high_performers"] == []
    assert temporal["by_year"][2025]["appearance_rates"][1] == 1
    assert temporal["by_year"][2026]["appearance_rates"][1] == 1
    assert (
        temporal["year_over_year_trends"]["consistent_performers"][0][
            "average_appearance_rate"
        ]
        == 1
    )
    assert analyzer.analyze_temporal_patterns() is temporal
    heatmap = analyzer._generate_heatmap_data()
    assert heatmap["by_year"]["appearance_rates_percent"][0] == [100, 100]
    assert heatmap["by_month"]["appearance_rates_percent"][0][2] is None


def test_rolling_windows_include_last_window_and_all_observed_months():
    analyzer = LotteryAnalyzer(dataset(10))
    rolling = analyzer._generate_trend_data()["consistency_trend"]
    assert len(rolling["data"]) == 1
    assert rolling["labels"] == ["01/10/2026"]
    data = dataset(0)
    data["results"] = [
        draw(datetime(2026, month, index + 1), numbers)
        for month, numbers, count in [
            (1, [1, 2, 3, 4, 5, 6], 20),
            (2, [7, 8, 9, 10, 11, 12], 20),
            (3, [20, 21, 22, 23, 24, 25], 1),
        ]
        for index in range(count)
    ]
    trends = LotteryAnalyzer(data)._generate_trend_data()
    assert trends["average_sum_trend"]["labels"] == ["2026-01", "2026-02", "2026-03"]
    assert trends["average_sum_trend"]["data"][-1] == 135


def test_winner_gaps_are_historical_not_overdue_forecasts():
    data = dataset(3)
    data["results"][0]["winners"] = "1"
    data["results"][1]["winners"] = "1"
    gaps = LotteryAnalyzer(data).get_winner_analysis()["next_win_probability"]
    assert gaps["as_of_date"] == "2026-01-03"
    assert gaps["days_since_last_win"] == 1
    assert "probability_status" not in gaps
    assert "expected_next_win_in_days" not in gaps


@pytest.mark.parametrize("maximum", [42, 45, 49, 55, 58])
def test_seeded_generators_return_valid_reproducible_picks(maximum):
    data = dataset(maximum=maximum)
    first = LotteryAnalyzer(data, rng=np.random.default_rng(42))
    second = LotteryAnalyzer(data, rng=np.random.default_rng(42))
    for method in (
        "generate_top_predictions",
        "generate_winning_predictions",
        "generate_pattern_based_prediction",
        "generate_ultimate_predictions",
    ):
        predictions = getattr(first, method)(5)
        assert predictions == getattr(second, method)(5)
        assert len(predictions) == 5
        for prediction in predictions:
            numbers = prediction["numbers"]
            assert len(numbers) == len(set(numbers)) == 6
            assert numbers == sorted(numbers)
            assert all(1 <= number <= maximum for number in numbers)


def test_shared_report_counts_only_unique_draws_and_preserves_requested_range():
    data = dataset(4)
    data["results"].append(deepcopy(data["results"][0]))
    report = build_analysis_report(data, "result_fixture.json")
    assert report["total_draws"] == report["overall_stats"]["total_draws"] == 4
    assert report["date_range"]["end"] == "2026-01-04"
    assert report["requested_date_range"]["end"] == "2026-12-31"
    assert report["analysis_version"] == "2"


def test_invalid_dataset_is_a_safe_client_error(client, result_file, settings):
    from pathlib import Path

    from app.storage import read_json, write_json

    path = Path(settings.DATA_PATH) / result_file
    data = read_json(path)
    data["results"][0]["numbers"] = [1, 1, 2, 3, 4, 5]
    write_json(path, data)
    assert (
        client.post("/api/analyze", json={"filename": result_file}).status_code == 400
    )
    assert client.get(f"/analyze/{result_file}").status_code == 400


@pytest.mark.parametrize(
    ("maximum", "label"), [(45, "Megalotto 6/45"), (49, "Superlotto 6/49")]
)
def test_official_scraper_game_spelling_is_normalized(maximum, label):
    data = dataset(1, maximum)
    data["results"][0]["game"] = label
    analyzer = LotteryAnalyzer(data)
    assert analyzer.results[0]["game"] == data["game_type"]
    assert analyzer.input_quality["game_labels_normalized"] == 1
    data["results"][0]["game"] = "Grand Lotto 6/55"
    with pytest.raises(DataValidationException, match="another game"):
        LotteryAnalyzer(data)


def test_saved_new_and_legacy_reports_render_with_correct_version_notice(
    client, settings
):
    from pathlib import Path

    from app.storage import write_json

    source = "result_fixture.json"
    data = dataset(40)
    write_json(Path(settings.DATA_PATH) / source, data)
    report = build_analysis_report(data, source)
    path = Path(settings.ANALYSIS_PATH) / "analysis_fixture.json"
    write_json(path, report)
    response = client.get("/view-report/analysis_fixture.json")
    assert response.status_code == 200
    assert b"Data Quality and Statistical Context" in response.data
    assert b"This is a legacy saved report" not in response.data
    report.pop("analysis_version")
    write_json(path, report)
    response = client.get("/view-report/analysis_fixture.json")
    assert response.status_code == 200
    assert b"This is a legacy saved report" in response.data
