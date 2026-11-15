"""Out-of-sample boundaries, equal ticket budgets, and persisted CLI results."""

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest
from test_analyzer import dataset

from app.exceptions import DataValidationException, InsufficientDataException
from app.modules.accuracy_analyzer import AccuracyAnalyzer
from app.services.analysis import select_analysis_snapshot
from app.services.evaluation import evaluate_walk_forward
from app.storage import read_json, write_json
from scripts import evaluate_analysis


def test_walk_forward_is_reproducible_and_respects_training_boundary():
    data = dataset(12)
    result = evaluate_walk_forward(
        data, evaluation_draws=3, min_training_draws=5, tickets=2, seed=7
    )
    assert result == evaluate_walk_forward(
        data, evaluation_draws=3, min_training_draws=5, tickets=2, seed=7
    )
    assert len(result["folds"]) == 3
    for fold in result["folds"]:
        assert datetime.strptime(fold["training_end"], "%m/%d/%Y") < datetime.strptime(
            fold["target_date"], "%m/%d/%Y"
        )
        for comparison in fold["comparisons"].values():
            assert len(comparison["tickets"]) == len(comparison["matches"]) == 2
    assert result["fair_draw_baseline"]["expected_matches_per_ticket"] == pytest.approx(
        36 / 42
    )
    assert sum(
        result["fair_draw_baseline"]["match_probabilities"].values()
    ) == pytest.approx(1)
    for metrics in result["summary"].values():
        assert (
            sum(metrics["match_distribution"].values()) == metrics["total_tickets"] == 6
        )
        assert len(metrics["mean_matches_95_interval"]) == 2
    assert result["uncertainty"]["comparison_adjustment"].startswith("Bonferroni")


def test_changing_unseen_outcome_cannot_change_its_generated_tickets():
    data = dataset(12)
    original = evaluate_walk_forward(
        data, evaluation_draws=3, min_training_draws=5, tickets=2
    )
    changed = deepcopy(data)
    changed["results"][9]["numbers"] = [1, 2, 3, 4, 5, 6]
    updated = evaluate_walk_forward(
        changed, evaluation_draws=3, min_training_draws=5, tickets=2
    )
    before, after = original["folds"][0], updated["folds"][0]
    assert before["training_sha256"] == after["training_sha256"]
    for name in before["comparisons"]:
        assert (
            before["comparisons"][name]["tickets"]
            == after["comparisons"][name]["tickets"]
        )
    assert original["dataset_sha256"] != updated["dataset_sha256"]


@pytest.mark.parametrize(
    "arguments",
    [
        {"evaluation_draws": 1},
        {"tickets": 0},
        {"tickets": 101},
        {"seed": -1},
        {"min_training_draws": True},
    ],
)
def test_evaluation_rejects_invalid_parameters(arguments):
    with pytest.raises(DataValidationException):
        evaluate_walk_forward(dataset(), **arguments)


def test_insufficient_unique_history_and_unequal_ticket_budgets_are_rejected():
    data = dataset(6)
    data["results"].extend(deepcopy(data["results"]))
    with pytest.raises(InsufficientDataException, match="unique draws"):
        evaluate_walk_forward(data, evaluation_draws=3, min_training_draws=5)
    data = dataset(6)
    for result in data["results"]:
        result["numbers"] = [1, 2, 3, 4, 5, 6]
    with pytest.raises(InsufficientDataException, match="equal-ticket"):
        evaluate_walk_forward(data, evaluation_draws=2, min_training_draws=2, tickets=2)


def test_cli_saves_separate_reports_and_does_not_modify_source(
    settings, tmp_path, monkeypatch
):
    monkeypatch.setattr(evaluate_analysis, "config", settings)
    settings.ANALYSIS_PATH = str(tmp_path / "analysis")
    filename = "result_fixture.json"
    source = Path(settings.DATA_PATH) / filename
    write_json(source, dataset(8))
    second_filename = "result_second_game.json"
    write_json(Path(settings.DATA_PATH) / second_filename, dataset(8, 45))
    before = source.read_bytes()
    assert (
        evaluate_analysis.main(
            [
                "--filename",
                filename,
                "--filename",
                second_filename,
                "--draws",
                "2",
                "--min-training",
                "2",
                "--tickets",
                "1",
                "--output",
                "evaluation_fixture.json",
            ]
        )
        == 0
    )
    saved = read_json(Path(settings.ANALYSIS_PATH) / "evaluation_fixture.json")
    assert saved["evaluations"][0]["method"] == "retrospective_walk_forward"
    assert saved["evaluations"][0]["source_file"] == filename
    assert [report["game_type"] for report in saved["evaluations"]] == [
        "Lotto 6/42",
        "Mega Lotto 6/45",
    ]
    assert source.read_bytes() == before
    with pytest.raises(SystemExit) as error:
        evaluate_analysis.main(["--filename", "../result_fixture.json"])
    assert error.value.code == 2
    assert evaluate_analysis.main(["--filename", "result_..\\fixture.json"]) == 1


def test_cli_failure_does_not_write_success_report(
    settings, tmp_path, monkeypatch, caplog
):
    monkeypatch.setattr(evaluate_analysis, "config", settings)
    settings.ANALYSIS_PATH = str(tmp_path / "analysis")
    write_json(Path(settings.DATA_PATH) / "result_small.json", dataset(3))
    assert (
        evaluate_analysis.main(
            [
                "--filename",
                "result_small.json",
                "--output",
                "evaluation_failed.json",
            ]
        )
        == 1
    )
    assert not (Path(settings.ANALYSIS_PATH) / "evaluation_failed.json").exists()
    assert "Evaluation failed" in caplog.text


def test_snapshot_selection_prefers_strictly_earlier_coverage(tmp_path):
    for name, generated, coverage in [
        ("prior", "2026-01-09 23:00:00", "2026-01-09"),
        ("same_day", "2026-01-10 23:00:00", "2026-01-10"),
    ]:
        write_json(
            tmp_path / f"analysis_result_Lotto_6-42_{name}.json",
            {
                "analyzed_at": generated,
                "date_range": {"end": coverage},
            },
        )
    snapshot = select_analysis_snapshot(
        "Lotto_6-42", str(tmp_path), datetime(2026, 1, 10)
    )
    assert snapshot is not None
    assert snapshot["selection_reason"] == "earlier_day_with_prior_coverage"


def test_accuracy_marks_retrospective_records_and_includes_ultimate(tmp_path):
    write_json(
        tmp_path / "accuracy_fixture.json",
        {
            "draw_date": "2026-01-10",
            "game_type": "Lotto 6/42",
            "actual_numbers": [1, 2, 3, 4, 5, 6],
            "analysis_snapshot": {
                "generated_at": "2026-01-11 01:00:00",
                "coverage_end": "2026-01-09",
            },
            "ultimate_predictions_comparison": [
                {
                    "rank": 1,
                    "predicted_numbers": [1, 2, 3, 4, 5, 6],
                    "matched_numbers": [1, 2, 3, 4, 5, 6],
                }
            ],
        },
    )
    analysis = AccuracyAnalyzer(str(tmp_path)).analyze_overall_accuracy()
    assert analysis["prediction_types"]["ultimate_predictions"]["jackpot_hits"] == 1
    assert analysis["match_distribution"]["total_predictions"] == 1
    assert (
        analysis["evaluation_context"]["snapshot_timing_counts"][
            "retrospective_or_unverified"
        ]
        == 1
    )
    assert analysis["game_breakdown"]["Lotto 6/42"][
        "expected_matches_per_ticket"
    ] == pytest.approx(36 / 42)
    assert analysis["best_algorithm"]["name"] == "Ultimate Predictions"
    json.dumps(analysis, allow_nan=False)


def test_result_submission_compares_ultimate_and_normalizes_winners(
    client, result_file, settings
):
    write_json(
        Path(settings.ANALYSIS_PATH) / "analysis_result_Lotto_6-42_prior.json",
        {
            "analyzed_at": "2026-11-01 23:00:00",
            "date_range": {"end": "2026-11-01"},
            "ultimate_predictions": [
                {
                    "numbers": [1, 2, 3, 4, 5, 6],
                    "ultimate_confidence_score": 80,
                }
            ],
        },
    )
    response = client.post(
        "/api/submit-actual-result",
        json={
            "game_type": "Lotto 6/42",
            "draw_date": "2026-11-02",
            "numbers": [1, 2, 3, 4, 5, 6],
            "winners": "0 ",
            "target_filename": result_file,
        },
    )
    assert response.status_code == 200
    results = response.json["accuracy_results"]
    assert results["ultimate_predictions_comparison"][0]["matches"] == 6
    assert results["analysis_snapshot"]["timing_status"] == "earlier_day_snapshot"
    saved = read_json(Path(settings.DATA_PATH) / result_file)
    assert saved["results"][0]["winners"] == "0"
