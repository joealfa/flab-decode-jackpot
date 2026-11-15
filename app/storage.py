"""Contained paths and atomic, cross-process JSON persistence."""

import json
import os
import tempfile
from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Any

from filelock import FileLock

from app.exceptions import BadRequestException


@cache
def json_lock(filepath: str) -> FileLock:
    """Reuse a reentrant file lock for nested operations on the same path."""
    return FileLock(filepath + ".lock")


def validate_filename(filename: str, allowed_dir: str) -> str:
    """Resolve a basename within its permitted directory.

    Args:
        filename: Untrusted basename.
        allowed_dir: Directory containing the resource.

    Returns:
        Contained absolute path.

    Raises:
        BadRequestException: If the path is not a contained JSON filename.
    """
    if (
        not isinstance(filename, str)
        or not filename
        or any(character in filename for character in ("/", "\\", ":", "\x00"))
        or not filename.endswith(".json")
    ):
        raise BadRequestException("Invalid JSON filename")
    directory = Path(allowed_dir).resolve()
    filepath = (directory / filename).resolve()
    if filepath.parent != directory:
        raise BadRequestException("Invalid filename")
    return str(filepath)


def read_json(filepath: str | Path) -> Any:
    """Read a UTF-8 JSON document."""
    path = Path(filepath)
    with json_lock(str(path.resolve())):
        with path.open(encoding="utf-8") as document:
            return json.load(document)


def write_json(filepath: str | Path, data: Any) -> None:
    """Atomically replace a JSON document under its cross-process lock."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with json_lock(str(path.resolve())):
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as document:
                json.dump(data, document, indent=2, ensure_ascii=False, allow_nan=False)
                document.flush()
                os.fsync(document.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def update_json(filepath: str | Path, mutation: Callable[[Any], Any]) -> Any:
    """Lock the entire read-modify-write transaction and return its result."""
    path = Path(filepath)
    with json_lock(str(path.resolve())):
        data = read_json(path)
        result = mutation(data)
        write_json(path, data)
        return result
