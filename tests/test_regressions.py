"""Regression coverage for the review's security and HTTP findings."""

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from app import create_app
from app.exceptions import BadRequestException, InvalidNumbersException
from app.storage import read_json, validate_filename, write_json
from app.validators import validate_lottery_numbers


@pytest.mark.parametrize(
    "filename",
    [
        "../outside.json",
        "..\\outside.json",
        "/tmp/outside.json",
        "C:\\outside.json",
        "note.txt",
        "",
        None,
        42,
    ],
)
def test_path_rejection(tmp_path, filename):
    """Reject traversal and invalid filename types on every platform."""
    with pytest.raises(BadRequestException):
        validate_filename(filename, str(tmp_path))


@pytest.mark.parametrize("value", [True, False, 1.8, 1.0, "1", None])
def test_numbers_are_strict_integers(value):
    """Never silently coerce JSON booleans, strings, or floating-point numbers."""
    with pytest.raises(InvalidNumbersException):
        validate_lottery_numbers([value, 2, 3, 4, 5, 6], "Lotto 6/42")


def test_valid_numbers():
    """Accept and sort six distinct in-range integers."""
    assert validate_lottery_numbers([6, 5, 4, 3, 2, 1], "Lotto 6/42") == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]


@pytest.mark.parametrize(
    "filename",
    ["../outside.json", "..\\outside.json", "result_Mega_Lotto_6-45_20261101.json"],
)
def test_submission_cannot_escape_game(client, result_file, settings, filename):
    """Reject paths outside the selected game's allowlist before writing."""
    assert (Path(settings.DATA_PATH) / result_file).is_file()
    outside = Path(settings.DATA_PATH).parent / "outside.json"
    original = {"game_type": "Lotto 6/42", "results": [], "total_draws": 0}
    write_json(outside, original)
    response = client.post(
        "/api/submit-actual-result",
        json={
            "game_type": "Lotto 6/42",
            "draw_date": "2026-11-06",
            "numbers": [1, 2, 3, 4, 5, 6],
            "target_filename": filename,
        },
    )
    assert response.status_code == 400
    assert read_json(outside) == original


def test_submission_checks_file_game(client, result_file, settings):
    """Reject a file whose content disagrees with its game-specific filename."""
    path = Path(settings.DATA_PATH) / result_file
    data = read_json(path)
    data["game_type"] = "Mega Lotto 6/45"
    write_json(path, data)
    response = client.post(
        "/api/submit-actual-result",
        json={
            "game_type": "Lotto 6/42",
            "draw_date": "2026-11-06",
            "numbers": [1, 2, 3, 4, 5, 6],
            "target_filename": result_file,
        },
    )
    assert response.status_code == 400
    assert read_json(path) == data


@pytest.mark.parametrize(
    "filename", ["analysis_../../outside.json", "analysis_..\\..\\outside.json"]
)
def test_ai_path_rejected_before_model_call(client, monkeypatch, filename):
    """Block traversal before an Ollama client is constructed."""
    monkeypatch.setattr(
        "app.routes.analysis.AIAnalyzer",
        lambda **_: pytest.fail("Model must not be called"),
    )
    assert (
        client.post("/api/ai-analyze", json={"filename": filename}).status_code == 400
    )


def test_list_failure_has_500_status(client, settings):
    """Corrupt metadata returns an error object and HTTP 500, not a JSON tuple."""
    (Path(settings.DATA_PATH) / "bad.json").write_text("not json", encoding="utf-8")
    response = client.get("/api/files")
    assert response.status_code == 500
    assert isinstance(response.json, dict) and response.json["success"] is False
    assert "details" not in response.json


def test_history_failure_has_500_status(client, settings):
    """Corrupt history metadata returns HTTP 500."""
    (Path(settings.ANALYSIS_PATH) / "analysis_result_bad_20261106.json").write_text(
        "not json", encoding="utf-8"
    )
    response = client.get("/api/analysis-history/result_bad.json")
    assert response.status_code == 500 and response.json["success"] is False


def test_factory_isolation(settings):
    """Multiple apps own distinct task state and do not start background jobs."""
    first, second = create_app(settings), create_app(settings)
    assert (
        first.extensions["progress_tracker"]
        is not second.extensions["progress_tracker"]
    )
    assert (
        first.extensions["scrape_semaphore"]
        is not second.extensions["scrape_semaphore"]
    )
    assert not first.extensions["scheduler"].running
    assert first.test_client().get("/").status_code == 200
    assert first.test_client().get("/accuracy-dashboard").status_code == 200
    assert first.test_client().get("/api/accuracy-summary").status_code == 404


def test_limiter_returns_json(settings):
    """Configured global rate limits cover API routes and return JSON errors."""
    application = create_app(
        replace(settings, RATE_LIMIT_ENABLED=True, RATE_LIMIT_GENERAL="1 per minute")
    )
    client = application.test_client()
    assert client.get("/api/files").status_code == 200
    response = client.get("/api/files")
    assert response.status_code == 429
    assert response.json is not None
    assert response.json["success"] is False


def test_limiter_isolation(settings):
    """A second app cannot disable another app's request limits."""
    first = create_app(
        replace(settings, RATE_LIMIT_ENABLED=True, RATE_LIMIT_GENERAL="1 per minute")
    )
    second = create_app(settings)
    client = first.test_client()
    assert client.get("/api/files").status_code == 200
    assert client.get("/api/files").status_code == 429
    assert second.test_client().get("/api/files").status_code == 200


def test_api_analysis_uses_shared_report(client, result_file, monkeypatch):
    """Keep the existing JSON contract when report generation moves into a service."""
    monkeypatch.setattr(
        "app.routes.analysis.build_analysis_report",
        lambda *args, **kwargs: (
            {"overall_stats": {"count": np.int64(1)}, "day_analysis": {},
             "top_predictions": [], "winning_predictions": [], "chart_data": {}}
            if args or kwargs
            else pytest.fail("Analysis arguments were not forwarded")
        ),
    )
    response = client.post("/api/analyze", json={"filename": result_file})
    assert response.status_code == 200
    assert response.json["overall_stats"]["count"] == 1


def test_real_analysis_and_saved_dashboard(client, result_file, settings):
    """Exercise real statistics, report persistence, and dashboard rendering."""
    from datetime import datetime, timedelta

    path = Path(settings.DATA_PATH) / result_file
    data = read_json(path)
    template = data["results"][0]
    data["results"] = [
        dict(
            template,
            date=(datetime(2026, 11, 1) - timedelta(days=index)).strftime("%m/%d/%Y"),
        )
        for index in range(14)
    ]
    data["total_draws"] = 14
    write_json(path, data)
    response = client.post("/api/analyze", json={"filename": result_file})
    assert response.status_code == 200
    assert response.json["overall_stats"]["total_draws"] == 14
    response = client.get(f"/analyze/{result_file}")
    assert response.status_code == 200
    reports = list(Path(settings.ANALYSIS_PATH).glob("*.json"))
    assert len(reports) == 1
    assert read_json(reports[0])["source_file"] == result_file


@pytest.mark.parametrize("body", [[], 123, {"filename": "../outside.json"}, {}])
def test_api_analysis_rejects_invalid_body(client, body):
    """Invalid bodies and paths are client errors rather than internal errors."""
    assert client.post("/api/analyze", json=body).status_code == 400


def _wait_for_ai(client, name, timeout=5.0):
    """Poll a background AI record until it leaves the pending states."""
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        record = client.get(f"/api/ai-analysis/{name}").json["analysis"]
        if record["status"] not in ("queued", "running"):
            return record
        time.sleep(0.02)
    pytest.fail(f"AI analysis {name} did not finish")


def _fake_analyzer(analyze=None, running=True):
    """Build an AIAnalyzer stand-in with configurable status and output."""

    class FakeAnalyzer:
        model = "fake-model"

        def __init__(self, **_):
            pass

        def check_ollama_status(self):
            return {"running": running, "model_available": True}

        def analyze_lottery_report(self, analysis_data):
            if analyze:
                return analyze(analysis_data)
            return {
                "success": True,
                "model": self.model,
                "game_type": analysis_data["game_type"],
                "analysis": f"Interpretation of {analysis_data['analyzed_at']}",
                "total_draws_analyzed": analysis_data["total_draws"],
            }

    return FakeAnalyzer


def _write_report(settings, result_file):
    report = "analysis_result_Lotto_6-42_20261101_20261102_000000.json"
    write_json(
        Path(settings.ANALYSIS_PATH) / report,
        {
            "analyzed_at": "2026-11-02 00:00:00",
            "source_file": result_file,
            "game_type": "Lotto 6/42",
            "date_range": {"start": "2026-11-01", "end": "2026-11-01"},
            "total_draws": 1,
        },
    )
    return report


def test_ai_analyses_are_saved_listed_and_deleted(
    client, result_file, settings, monkeypatch
):
    """Every AI run is queued, persisted, and can be compared later."""
    monkeypatch.setattr("app.routes.analysis.AIAnalyzer", _fake_analyzer())
    report = _write_report(settings, result_file)

    first = client.post("/api/ai-analyze", json={"filename": report})
    assert first.status_code == 202
    assert first.json["status"] == "queued"
    _wait_for_ai(client, first.json["ai_filename"])
    second = client.post("/api/ai-analyze", json={"filename": result_file})
    assert second.status_code == 202
    queued = [first.json["ai_filename"], second.json["ai_filename"]]
    assert queued[0] != queued[1]
    records = [_wait_for_ai(client, name) for name in queued]
    assert all(record["status"] == "completed" for record in records)

    history = client.get(f"/api/ai-analysis-history/{result_file}").json
    assert history["count"] == 2
    assert {item["analysis_report"] for item in history["analyses"]} == {report}
    assert {item["status"] for item in history["analyses"]} == {"completed"}

    name = queued[0]
    record = client.get(f"/api/ai-analysis/{name}").json["analysis"]
    assert record["analysis"] == "Interpretation of 2026-11-02 00:00:00"
    assert record["source_file"] == result_file

    assert client.delete(f"/api/ai-analysis/{name}").status_code == 200
    assert client.get(f"/api/ai-analysis/{name}").status_code == 404
    assert client.get(f"/api/ai-analysis-history/{result_file}").json["count"] == 1


def test_ai_timeout_recorded_without_internal_details(
    client, result_file, settings, monkeypatch
):
    """A model timeout becomes a failed history entry with a safe explanation."""
    import httpx

    def time_out(_):
        try:
            raise httpx.ReadTimeout("internal socket detail")
        except httpx.ReadTimeout as error:
            raise RuntimeError("AI analysis failed") from error

    monkeypatch.setattr(
        "app.routes.analysis.AIAnalyzer", _fake_analyzer(analyze=time_out)
    )
    report = _write_report(settings, result_file)
    response = client.post("/api/ai-analyze", json={"filename": report})
    record = _wait_for_ai(client, response.json["ai_filename"])
    assert record["status"] == "failed"
    assert "did not respond" in record["error"]
    assert "internal socket detail" not in record["error"]


def test_duplicate_ai_request_reuses_pending_run(
    client, application, result_file, settings, monkeypatch
):
    """Repeated clicks while a report is queued do not start more model runs."""
    monkeypatch.setattr("app.routes.analysis.AIAnalyzer", _fake_analyzer())
    report = _write_report(settings, result_file)
    semaphore = application.extensions["ai_semaphore"]
    semaphore.acquire()
    try:
        first = client.post("/api/ai-analyze", json={"filename": report}).json
        second = client.post("/api/ai-analyze", json={"filename": report}).json
        assert second["already_pending"] is True
        assert second["ai_filename"] == first["ai_filename"]
    finally:
        semaphore.release()
    assert _wait_for_ai(client, first["ai_filename"])["status"] == "completed"


def test_interrupted_ai_runs_marked_failed(settings, result_file):
    """Pending runs from a stopped process are not shown as running forever."""
    from app.services.ai_history import (
        create_pending_ai_analysis,
        fail_interrupted_ai_analyses,
        load_ai_analysis,
    )

    record = create_pending_ai_analysis(
        settings.AI_ANALYSIS_PATH,
        "analysis_x.json",
        {"source_file": result_file},
        "fake-model",
    )
    assert fail_interrupted_ai_analyses(settings.AI_ANALYSIS_PATH) == 1
    saved = load_ai_analysis(settings.AI_ANALYSIS_PATH, record["filename"])
    assert saved["status"] == "failed"
    assert "restarted" in saved["error"]


def test_ollama_unavailable_message_reaches_client(
    client, result_file, settings, monkeypatch
):
    """Users see why AI analysis cannot start instead of a generic 500."""
    monkeypatch.setattr(
        "app.routes.analysis.AIAnalyzer", _fake_analyzer(running=False)
    )
    report = _write_report(settings, result_file)
    response = client.post("/api/ai-analyze", json={"filename": report})
    assert response.status_code == 503
    assert "Ollama is not running" in response.json["error"]
    assert list(Path(settings.AI_ANALYSIS_PATH).glob("ai_*.json")) == []


@pytest.mark.parametrize("name", ["analysis_x.json", "ai_..\\outside.json"])
def test_ai_record_rejects_other_files(client, name):
    """Only contained AI records can be read through the AI history API."""
    assert client.get(f"/api/ai-analysis/{name}").status_code == 400


def test_finished_progress_removed_without_scheduler(
    client, application, settings, monkeypatch
):
    """Leftover progress files are cleaned when a scrape starts, honoring the age."""
    import time

    progress_dir = Path(settings.PROGRESS_PATH)
    now = time.time()
    for name, finished in (("old", now - settings.PROGRESS_CLEANUP_AGE - 5), ("new", now)):
        write_json(
            progress_dir / f"{name}.json",
            {"status": "completed", "updated_at": finished, "completed_at": finished},
        )
    semaphore = application.extensions["scrape_semaphore"]
    monkeypatch.setattr(
        "app.routes.scraping.scrape_data_thread", lambda *args: semaphore.release()
    )
    response = client.post(
        "/scrape",
        json={
            "game_type": "Lotto 6/42",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        },
    )
    assert response.status_code == 200
    remaining = {path.stem for path in progress_dir.glob("*.json")}
    assert remaining == {"new", response.json["task_id"]}


def test_unsafe_network_configuration_rejected(settings):
    """Network exposure is rejected without credentials and TLS safeguards."""
    with pytest.raises(ValueError, match="authentication"):
        replace(settings, HOST="0.0.0.0")
    with pytest.raises(ValueError, match="TLS"):
        replace(
            settings,
            HOST="0.0.0.0",
            BASIC_AUTH_USERNAME="test",
            BASIC_AUTH_PASSWORD="test",
        )


def test_worker_releases_slot_on_failure(application, settings, monkeypatch):
    """A failed browser operation cannot permanently exhaust the scrape slot."""
    from datetime import datetime

    from app.services.jobs import scrape_data_thread

    def fail(**kwargs):
        """Simulate browser initialization failure."""
        raise RuntimeError(f"internal browser path: {kwargs!r}")

    monkeypatch.setattr("app.services.jobs.PCSOScraper", fail)
    semaphore = application.extensions["scrape_semaphore"]
    tracker = application.extensions["progress_tracker"]
    semaphore.acquire()
    scrape_data_thread(
        "test-task",
        "Lotto 6/42",
        datetime(2026, 11, 1),
        datetime(2026, 11, 6),
        settings.DATA_PATH,
        tracker,
        semaphore,
        settings,
    )
    assert semaphore.acquire(blocking=False)
    semaphore.release()
    progress = tracker.get_progress("test-task")
    assert progress is not None
    assert progress["status"] == "failed"
    assert "internal browser path" not in progress["message"]


def test_scrape_concurrency(client, application):
    """Reject additional scrape jobs while the single-process slot is occupied."""
    semaphore = application.extensions["scrape_semaphore"]
    semaphore.acquire()
    try:
        response = client.post(
            "/scrape",
            json={
                "game_type": "Lotto 6/42",
                "start_date": "2026-11-01",
                "end_date": "2026-11-06",
            },
        )
        assert response.status_code == 429
    finally:
        semaphore.release()


def test_numpy_json_provider(application):
    """Normalize scientific values for every JSON route, including nested arrays."""
    with application.app_context():
        assert application.json.loads(
            application.json.dumps(
                {
                    "values": np.array([1, 2]),
                    "count": np.int64(2),
                    "flag": np.bool_(True),
                }
            )
        ) == {"values": [1, 2], "count": 2, "flag": True}


def test_config_reads_current_environment(monkeypatch, settings):
    """Configuration defaults reflect the environment at construction time."""
    monkeypatch.setenv("PORT", "5432")
    fresh = replace(settings, PORT=5432)
    from app.config import Config

    assert (
        Config(
            HOST="127.0.0.1",
            BASIC_AUTH_USERNAME="",
            BASIC_AUTH_PASSWORD="",
            SSL_CERTFILE="",
            SSL_KEYFILE="",
        ).PORT
        == fresh.PORT
    )


def test_basic_auth(settings):
    """Challenge missing credentials and accept configured Basic Auth."""
    client = create_app(
        replace(
            settings,
            BASIC_AUTH_USERNAME="test-user",
            BASIC_AUTH_PASSWORD="test-only-password",
        )
    ).test_client()
    assert client.get("/health").status_code == 401
    assert (
        client.get("/health", auth=("test-user", "test-only-password")).status_code
        == 200
    )
