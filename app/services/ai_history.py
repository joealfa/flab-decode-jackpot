"""Persistence for AI interpretations so earlier runs can be reviewed later."""

import logging
import os
from datetime import datetime
from typing import Any

from app.exceptions import BadRequestException, DataNotFoundException
from app.storage import read_json, update_json, validate_filename, write_json

logger = logging.getLogger(__name__)

AI_PREFIX = "ai_"
PREVIEW_LENGTH = 240
STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
PENDING_STATUSES = frozenset({STATUS_QUEUED, STATUS_RUNNING})


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _source_base(source_file: str) -> str:
    return os.path.splitext(source_file)[0]


def validate_ai_filename(filename: str, ai_dir: str) -> str:
    """Resolve a stored AI analysis filename within its directory."""
    if not isinstance(filename, str) or not filename.startswith(AI_PREFIX):
        raise BadRequestException("Invalid AI analysis filename")
    return validate_filename(filename, ai_dir)


def create_pending_ai_analysis(
    ai_dir: str,
    analysis_report: str,
    analysis_data: dict,
    model: str,
) -> dict:
    """Create a queued AI record so a background run is visible in history.

    Args:
        ai_dir: Directory for AI analysis records.
        analysis_report: Basename of the statistical report used as input.
        analysis_data: Loaded statistical report.
        model: Ollama model that will produce the interpretation.

    Returns:
        The persisted record, including its ``filename``.
    """
    source_file = analysis_data.get("source_file") or ""
    if not source_file.endswith(".json"):
        source_file = analysis_report.removeprefix("analysis_")
    now = datetime.now()
    filename = (
        f"{AI_PREFIX}{_source_base(source_file)}_{now.strftime('%Y%m%d_%H%M%S_%f')}.json"
    )
    record = {
        "filename": filename,
        "status": STATUS_QUEUED,
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "source_file": source_file,
        "analysis_report": analysis_report,
        "analysis_analyzed_at": analysis_data.get("analyzed_at"),
        "game_type": analysis_data.get("game_type"),
        "date_range": analysis_data.get("date_range", {}),
        "total_draws_analyzed": None,
        "model": model,
        "analysis": "",
        "error": None,
    }
    write_json(validate_ai_filename(filename, ai_dir), record)
    logger.info("Queued AI analysis: %s", filename)
    return record


def _update_ai_record(ai_dir: str, filename: str, changes: dict) -> bool:
    """Apply changes unless the user deleted the record while it was pending."""
    path = validate_ai_filename(filename, ai_dir)

    def apply(record: dict) -> None:
        record.update(changes, updated_at=_timestamp())

    try:
        update_json(path, apply)
    except FileNotFoundError:
        logger.info("AI analysis %s was deleted before it finished", filename)
        return False
    return True


def mark_ai_analysis_running(ai_dir: str, filename: str) -> bool:
    """Record that the model has started processing a queued analysis."""
    return _update_ai_record(ai_dir, filename, {"status": STATUS_RUNNING})


def complete_ai_analysis(ai_dir: str, filename: str, ai_result: dict) -> bool:
    """Store the model output for a pending analysis."""
    changes = {
        "status": STATUS_COMPLETED,
        "completed_at": _timestamp(),
        "total_draws_analyzed": ai_result.get("total_draws_analyzed"),
        "model": ai_result.get("model"),
        "analysis": ai_result.get("analysis", ""),
        "error": None,
    }
    if ai_result.get("game_type"):
        changes["game_type"] = ai_result["game_type"]
    return _update_ai_record(ai_dir, filename, changes)


def fail_ai_analysis(ai_dir: str, filename: str, message: str) -> bool:
    """Record a client-safe failure message for a pending analysis."""
    return _update_ai_record(
        ai_dir, filename, {"status": STATUS_FAILED, "error": message}
    )


def fail_interrupted_ai_analyses(ai_dir: str) -> int:
    """Fail pending records left behind when a previous server process stopped."""
    if not os.path.isdir(ai_dir):
        return 0
    count = 0
    for filename in os.listdir(ai_dir):
        if not filename.startswith(AI_PREFIX) or not filename.endswith(".json"):
            continue
        try:
            record = read_json(os.path.join(ai_dir, filename))
            if record.get("status") in PENDING_STATUSES and fail_ai_analysis(
                ai_dir,
                filename,
                "Interrupted because the server restarted. Please run it again.",
            ):
                count += 1
        except Exception:
            logger.error("Failed to recover AI analysis %s", filename, exc_info=True)
    return count


def find_pending_ai_analysis(
    ai_dir: str, source_file: str, analysis_report: str
) -> dict | None:
    """Return an unfinished run for the same report, if any."""
    for item in list_ai_analyses(ai_dir, source_file):
        if (
            item["status"] in PENDING_STATUSES
            and item["analysis_report"] == analysis_report
        ):
            return item
    return None


def list_ai_analyses(ai_dir: str, source_file: str) -> list[dict[str, Any]]:
    """Summarize saved AI interpretations for a result file, newest first."""
    if not os.path.isdir(ai_dir):
        return []
    prefix = f"{AI_PREFIX}{_source_base(source_file)}_"
    records = []
    for filename in os.listdir(ai_dir):
        if not filename.startswith(prefix) or not filename.endswith(".json"):
            continue
        try:
            record = read_json(os.path.join(ai_dir, filename))
        except Exception:
            logger.error("Failed to read AI analysis %s", filename, exc_info=True)
            continue
        if record.get("source_file") != source_file:
            continue
        text = record.get("analysis") or ""
        records.append(
            {
                "filename": filename,
                # Records saved before background runs existed have no status.
                "status": record.get("status", STATUS_COMPLETED),
                "error": record.get("error"),
                "created_at": record.get("created_at"),
                "analysis_report": record.get("analysis_report"),
                "analysis_analyzed_at": record.get("analysis_analyzed_at"),
                "game_type": record.get("game_type"),
                "date_range": record.get("date_range", {}),
                "total_draws_analyzed": record.get("total_draws_analyzed"),
                "model": record.get("model"),
                "preview": text[:PREVIEW_LENGTH],
            }
        )
    records.sort(key=lambda item: (item["created_at"] or "", item["filename"]), reverse=True)
    return records


def load_ai_analysis(ai_dir: str, filename: str) -> dict:
    """Load one saved AI interpretation."""
    path = validate_ai_filename(filename, ai_dir)
    if not os.path.exists(path):
        raise DataNotFoundException(filename)
    record = read_json(path)
    record.setdefault("status", STATUS_COMPLETED)
    return record


def delete_ai_analysis(ai_dir: str, filename: str) -> None:
    """Delete one saved AI interpretation."""
    path = validate_ai_filename(filename, ai_dir)
    if not os.path.exists(path):
        raise DataNotFoundException(filename)
    os.remove(path)
    logger.info("Deleted AI analysis: %s", filename)
