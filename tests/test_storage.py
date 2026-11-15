"""Concurrency, write-failure, and task-completion storage regressions."""

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

import pytest

from app.modules.progress_tracker import ProgressTracker
from app.services.results import submit_draw
from app.storage import read_json, update_json, write_json


def increment_in_process(path: str) -> None:
    """Increment a counter in a separately spawned worker process."""

    def mutate(data: dict) -> None:
        """Apply one locked increment."""
        data["count"] += 1

    update_json(path, mutate)


def test_cross_process_updates_preserved(tmp_path):
    """Repository locks coordinate separate processes, not only Python threads."""
    path = tmp_path / "counter.json"
    write_json(path, {"count": 0})
    with ProcessPoolExecutor(max_workers=2) as pool:
        list(pool.map(increment_in_process, [str(path)] * 12))
    assert read_json(path)["count"] == 12


def test_concurrent_updates_preserved(tmp_path):
    """Lock the whole transaction rather than only the final replacement."""
    path = tmp_path / "counter.json"
    write_json(path, {"count": 0})

    def increment(_):
        """Increment while holding the repository lock."""

        def mutate(data):
            """Apply one increment."""
            data["count"] += 1

        update_json(path, mutate)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(increment, range(40)))
    assert read_json(path)["count"] == 40


def test_failed_write_preserves_original(tmp_path):
    """Serialization failure cannot truncate an existing document."""
    path = tmp_path / "result.json"
    write_json(path, {"original": True})
    with pytest.raises(TypeError):
        write_json(path, {"invalid": object()})
    assert read_json(path) == {"original": True}
    assert not list(tmp_path.glob("*.tmp"))


def test_completed_task_has_result(tmp_path):
    """The completed state and result become visible together."""
    tracker = ProgressTracker(str(tmp_path))
    tracker.update_progress("task", 10, 100)
    tracker.complete_task("task", result={"filename": "result.json"})
    data = tracker.get_progress("task")
    assert data is not None
    assert data["status"] == "completed"
    assert data["result"]["filename"] == "result.json"


def test_interrupted_tasks_marked_failed(tmp_path):
    """Unfinished tasks from a previous process fail; finished ones are kept."""
    tracker = ProgressTracker(str(tmp_path))
    tracker.update_progress("running", 40, 100, "Extracting...")
    tracker.update_progress("done", 10, 100)
    tracker.complete_task("done", result={"filename": "result.json"})

    assert tracker.fail_interrupted_tasks() == 1

    running = tracker.get_progress("running")
    assert running is not None
    assert running["status"] == "failed"
    assert "interrupted" in running["message"]
    done = tracker.get_progress("done")
    assert done is not None and done["status"] == "completed"
    assert tracker.fail_interrupted_tasks() == 0


def test_draw_update_is_idempotent(result_file, settings):
    """Repeated submissions replace one draw without inflating its count."""
    path = str(Path(settings.DATA_PATH) / result_file)
    draw = {"date": "11/06/2026", "numbers": [1, 2, 3, 4, 5, 6]}
    first, updated = submit_draw(path, "Lotto 6/42", draw)
    assert not updated and first["total_draws"] == 2
    second, updated = submit_draw(path, "Lotto 6/42", draw)
    assert updated and second["total_draws"] == 2
