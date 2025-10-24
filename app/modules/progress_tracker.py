"""
Progress tracking for long-running operations.
"""

import json
import os
import time
import tempfile
from typing import Dict, Optional


class ProgressTracker:
    """Tracks progress of scraping operations."""

    def __init__(self, progress_dir: str = "app/data/progress"):
        """
        Initialize progress tracker.

        Args:
            progress_dir: Directory to store progress files
        """
        self.progress_dir = progress_dir
        os.makedirs(progress_dir, exist_ok=True)

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

        with open(progress_file, "w") as f:
            json.dump(data, f)

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
        temp_fd, temp_path = tempfile.mkstemp(dir=self.progress_dir, suffix='.json')
        try:
            with os.fdopen(temp_fd, 'w') as f:
                json.dump(data, f)
            os.replace(temp_path, progress_file)  # Atomic operation
        except Exception:
            # Clean up temp file if something goes wrong
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

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

    def complete_task(self, task_id: str, message: str = "Completed") -> None:
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

        # Write to temp file first, then atomic rename to avoid race conditions
        temp_fd, temp_path = tempfile.mkstemp(dir=self.progress_dir, suffix='.json')
        try:
            with os.fdopen(temp_fd, 'w') as f:
                json.dump(data, f)
            os.replace(temp_path, progress_file)  # Atomic operation
        except Exception:
            # Clean up temp file if something goes wrong
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

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

        # Write to temp file first, then atomic rename to avoid race conditions
        temp_fd, temp_path = tempfile.mkstemp(dir=self.progress_dir, suffix='.json')
        try:
            with os.fdopen(temp_fd, 'w') as f:
                json.dump(data, f)
            os.replace(temp_path, progress_file)  # Atomic operation
        except Exception:
            # Clean up temp file if something goes wrong
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def cleanup_task(self, task_id: str) -> None:
        """Remove progress file for a task."""
        progress_file = os.path.join(self.progress_dir, f"{task_id}.json")

        if os.path.exists(progress_file):
            os.remove(progress_file)

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

                # Check if task is completed or failed
                status = data.get("status", "")
                updated_at = data.get("updated_at", 0)
                age = current_time - updated_at

                # Clean up completed/failed tasks older than max_age
                if status in ["completed", "failed"] and age > max_age_seconds:
                    os.remove(filepath)
                    cleaned_count += 1

            except (json.JSONDecodeError, IOError):
                # If file is corrupted, remove it
                try:
                    os.remove(filepath)
                    cleaned_count += 1
                except OSError:
                    pass

        return cleaned_count

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

            except (json.JSONDecodeError, IOError):
                # If file is corrupted, remove it
                try:
                    os.remove(filepath)
                    cleaned_count += 1
                except OSError:
                    pass

        return cleaned_count
