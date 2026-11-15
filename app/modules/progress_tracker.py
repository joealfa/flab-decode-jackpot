"""
Progress tracking for long-running operations.
"""

import json
import os
import tempfile
import time
from functools import wraps
from typing import Dict, Optional

from app.storage import json_lock, validate_filename, write_json


def locked_task(method):
    """Serialize each task operation across threads and processes."""

    @wraps(method)
    def wrapped(self, task_id, *args, **kwargs):
        """Run a contained task operation while holding its lock."""
        filepath = validate_filename(f"{task_id}.json", self.progress_dir)
        with json_lock(os.path.join(self.progress_dir, ".tasks")), json_lock(filepath):
            return method(self, task_id, *args, **kwargs)

    return wrapped


def locked_cleanup(method):
    """Prevent cleanup from removing a task while it is being updated."""

    @wraps(method)
    def wrapped(self, *args, **kwargs):
        """Run cleanup under the same directory lock as task mutations."""
        with json_lock(os.path.join(self.progress_dir, ".tasks")):
            return method(self, *args, **kwargs)

    return wrapped


class ProgressTracker:
    """Tracks progress of scraping operations."""

    def __init__(
        self, progress_dir: str = "app/data/progress", completed_max_age: int = 180
    ):
        """
        Initialize progress tracker.

        Args:
            progress_dir: Directory to store progress files
            completed_max_age: Seconds to keep finished tasks so clients can read
                their final status before cleanup removes them
        """
        # Convert to absolute path to avoid path mismatch issues on Windows
        self.progress_dir = os.path.abspath(progress_dir)
        self.completed_max_age = completed_max_age
        os.makedirs(self.progress_dir, exist_ok=True)

    @locked_task
    def create_task(self, task_id: str) -> None:
        """Create a new progress tracking task."""
        progress_file = os.path.join(self.progress_dir, f"{task_id}.json")
        data = {
            "task_id": task_id,
            "status": "started",
            "current": 0,
            "total": 0,
            "percentage": 0,
            "message": "Initializing...",
            "started_at": time.time(),
            "updated_at": time.time(),
        }

        write_json(progress_file, data)

    @locked_task
    def update_progress(
        self, task_id: str, current: int, total: int, message: Optional[str] = None
    ) -> None:
        """Update progress for a task."""
        progress_file = os.path.join(self.progress_dir, f"{task_id}.json")

        if not os.path.exists(progress_file):
            self.create_task(task_id)

        with open(progress_file, "r") as f:
            data = json.load(f)

        data["current"] = current
        data["total"] = total
        data["percentage"] = int((current / total * 100)) if total > 0 else 0
        data["updated_at"] = time.time()

        if message:
            data["message"] = message

        # Write to temp file first, then atomic rename to avoid race conditions
        # Use delete=False to manually control file cleanup
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.progress_dir, suffix=".json", prefix="tmp_progress_"
        )
        try:
            with os.fdopen(temp_fd, "w") as f:
                json.dump(data, f)

            # Ensure both paths are absolute for Windows compatibility
            abs_temp_path = os.path.abspath(temp_path)
            abs_progress_file = os.path.abspath(progress_file)

            # Retry mechanism for Windows file locking issues
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # On Windows, os.replace() requires both paths to be on same drive
                    os.replace(abs_temp_path, abs_progress_file)
                    break  # Success, exit retry loop
                except PermissionError as perm_err:
                    if attempt < max_retries - 1:
                        # Wait a bit and retry
                        time.sleep(0.05)  # 50ms delay
                    else:
                        # Last attempt failed, raise
                        raise perm_err
        except Exception as e:
            # Clean up temp file if something goes wrong
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except OSError:
                pass
            # Re-raise with more context
            raise Exception(
                f"Failed to update progress for task {task_id}: {str(e)}"
            ) from e

    @locked_task
    def get_progress(self, task_id: str) -> Optional[Dict]:
        """Get progress for a task."""
        progress_file = os.path.join(self.progress_dir, f"{task_id}.json")

        if not os.path.exists(progress_file):
            return None

        # Retry logic to handle race conditions
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(progress_file, "r") as f:
                    content = f.read()
                    if not content:  # Empty file, retry
                        if attempt < max_retries - 1:
                            time.sleep(0.01)  # Wait 10ms before retry
                            continue
                        return None
                    return json.loads(content)
            except json.JSONDecodeError:
                # File is being written, retry
                if attempt < max_retries - 1:
                    time.sleep(0.01)  # Wait 10ms before retry
                    continue
                # If all retries fail, return None instead of crashing
                return None
            except Exception:
                # For any other error, return None
                return None

        return None

    @locked_task
    def complete_task(
        self, task_id: str, message: str = "Completed", result: Optional[Dict] = None
    ) -> None:
        """Mark a task as completed."""
        progress_file = os.path.join(self.progress_dir, f"{task_id}.json")

        if not os.path.exists(progress_file):
            return

        with open(progress_file, "r") as f:
            data = json.load(f)

        data["status"] = "completed"
        data["message"] = message
        data["percentage"] = 100
        data["updated_at"] = time.time()
        data["completed_at"] = time.time()  # Add completion timestamp
        if result is not None:
            data["result"] = result

        # Write to temp file first, then atomic rename to avoid race conditions
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.progress_dir, suffix=".json", prefix="tmp_progress_"
        )
        try:
            with os.fdopen(temp_fd, "w") as f:
                json.dump(data, f)

            # Ensure both paths are absolute for Windows compatibility
            abs_temp_path = os.path.abspath(temp_path)
            abs_progress_file = os.path.abspath(progress_file)

            # Retry mechanism for Windows file locking issues
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    os.replace(abs_temp_path, abs_progress_file)
                    break
                except PermissionError as perm_err:
                    if attempt < max_retries - 1:
                        time.sleep(0.05)
                    else:
                        raise perm_err
        except Exception as e:
            # Clean up temp file if something goes wrong
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except OSError:
                pass
            raise Exception(f"Failed to complete task {task_id}: {str(e)}") from e

    @locked_task
    def fail_task(self, task_id: str, error_message: str) -> None:
        """Mark a task as failed."""
        progress_file = os.path.join(self.progress_dir, f"{task_id}.json")

        if not os.path.exists(progress_file):
            return

        with open(progress_file, "r") as f:
            data = json.load(f)

        data["status"] = "failed"
        data["message"] = error_message
        data["updated_at"] = time.time()
        data["failed_at"] = time.time()  # Add failure timestamp

        # Write to temp file first, then atomic rename to avoid race conditions
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.progress_dir, suffix=".json", prefix="tmp_progress_"
        )
        try:
            with os.fdopen(temp_fd, "w") as f:
                json.dump(data, f)

            # Ensure both paths are absolute for Windows compatibility
            abs_temp_path = os.path.abspath(temp_path)
            abs_progress_file = os.path.abspath(progress_file)

            # Retry mechanism for Windows file locking issues
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    os.replace(abs_temp_path, abs_progress_file)
                    break
                except PermissionError as perm_err:
                    if attempt < max_retries - 1:
                        time.sleep(0.05)
                    else:
                        raise perm_err
        except Exception as e:
            # Clean up temp file if something goes wrong
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except OSError:
                pass
            raise Exception(f"Failed to mark task {task_id} as failed: {str(e)}") from e

    @locked_task
    def cleanup_task(self, task_id: str) -> None:
        """Remove progress file for a task."""
        progress_file = os.path.join(self.progress_dir, f"{task_id}.json")

        if os.path.exists(progress_file):
            os.remove(progress_file)

    @locked_cleanup
    def cleanup_completed_tasks(self, max_age_seconds: int = 300) -> int:
        """
        Clean up completed or failed tasks older than specified age.

        Args:
            max_age_seconds: Maximum age in seconds for completed tasks (default: 5 minutes)

        Returns:
            Number of tasks cleaned up
        """
        if not os.path.exists(self.progress_dir):
            return 0

        current_time = time.time()
        cleaned_count = 0

        for filename in os.listdir(self.progress_dir):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(self.progress_dir, filename)

            try:
                with open(filepath, "r") as f:
                    data = json.load(f)


                status = data.get("status", "")

                # Use completion/failure timestamp if available, otherwise updated_at
                completion_time = (
                    data.get("completed_at")
                    or data.get("failed_at")
                    or data.get("updated_at", 0)
                )
                age = current_time - completion_time

                # Clean up completed/failed tasks older than max_age
                if status in ["completed", "failed"] and age > max_age_seconds:
                    os.remove(filepath)
                    cleaned_count += 1

            except json.JSONDecodeError, IOError, OSError:
                # If file is corrupted or inaccessible, remove it
                try:
                    os.remove(filepath)
                    cleaned_count += 1
                except OSError:
                    pass

        return cleaned_count

    @locked_cleanup
    def cleanup_stale_tasks(self, max_age_seconds: int = 600) -> int:
        """
        Clean up stale tasks (stuck in 'started' status) that haven't been updated.

        Args:
            max_age_seconds: Maximum age in seconds for stale tasks (default: 10 minutes)

        Returns:
            Number of tasks cleaned up
        """
        if not os.path.exists(self.progress_dir):
            return 0

        current_time = time.time()
        cleaned_count = 0

        for filename in os.listdir(self.progress_dir):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(self.progress_dir, filename)

            try:
                with open(filepath, "r") as f:
                    data = json.load(f)

                status = data.get("status", "")
                updated_at = data.get("updated_at", 0)
                age = current_time - updated_at

                # Clean up tasks stuck in 'started' state for too long
                if status == "started" and age > max_age_seconds:
                    os.remove(filepath)
                    cleaned_count += 1

            except json.JSONDecodeError, IOError, OSError:
                # If file is corrupted, remove it
                try:
                    os.remove(filepath)
                    cleaned_count += 1
                except OSError:
                    pass

        return cleaned_count

    @locked_cleanup
    def cleanup_all_old_tasks(self, max_age_hours: int = 24) -> int:
        """
        Clean up all tasks (regardless of status) older than specified hours.

        Args:
            max_age_hours: Maximum age in hours (default: 24 hours)

        Returns:
            Number of tasks cleaned up
        """
        if not os.path.exists(self.progress_dir):
            return 0

        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned_count = 0

        for filename in os.listdir(self.progress_dir):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(self.progress_dir, filename)

            try:
                with open(filepath, "r") as f:
                    data = json.load(f)

                updated_at = data.get("updated_at", 0)
                age = current_time - updated_at

                if age > max_age_seconds:
                    os.remove(filepath)
                    cleaned_count += 1

            except json.JSONDecodeError, IOError, OSError:
                # If file is corrupted, remove it
                try:
                    os.remove(filepath)
                    cleaned_count += 1
                except OSError:
                    pass

        return cleaned_count

    @locked_cleanup
    def fail_interrupted_tasks(self) -> int:
        """Mark unfinished tasks as failed; scrape threads do not survive a restart."""
        if not os.path.exists(self.progress_dir):
            return 0

        recovered = 0
        for filename in os.listdir(self.progress_dir):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(self.progress_dir, filename)
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
            except json.JSONDecodeError, OSError:
                continue
            if data.get("status") != "started":
                continue
            now = time.time()
            data["status"] = "failed"
            data["message"] = (
                "Data loading was interrupted by a server restart. Please try again."
            )
            data["updated_at"] = now
            data["failed_at"] = now
            write_json(filepath, data)
            recovered += 1
        return recovered

    def cleanup_all(self) -> Dict[str, int]:
        """
        Comprehensive cleanup of all old and stale progress files.

        Returns:
            Dictionary with counts of different cleanup operations
        """
        completed_count = self.cleanup_completed_tasks(
            max_age_seconds=self.completed_max_age
        )
        stale_count = self.cleanup_stale_tasks(
            max_age_seconds=600
        )  # 10 minutes for stale
        old_count = self.cleanup_all_old_tasks(max_age_hours=24)  # 24 hours for any

        return {
            "completed_cleaned": completed_count,
            "stale_cleaned": stale_count,
            "old_cleaned": old_count,
            "total_cleaned": completed_count + stale_count + old_count,
        }
