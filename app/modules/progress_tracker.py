"""
Progress tracking for long-running operations.
"""

import json
import os
import time
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
            'task_id': task_id,
            'status': 'started',
            'current': 0,
            'total': 0,
            'percentage': 0,
            'message': 'Initializing...',
            'started_at': time.time(),
            'updated_at': time.time()
        }

        with open(progress_file, 'w') as f:
            json.dump(data, f)

    def update_progress(
        self,
        task_id: str,
        current: int,
        total: int,
        message: Optional[str] = None
    ) -> None:
        """Update progress for a task."""
        progress_file = os.path.join(self.progress_dir, f"{task_id}.json")

        if not os.path.exists(progress_file):
            self.create_task(task_id)

        with open(progress_file, 'r') as f:
            data = json.load(f)

        data['current'] = current
        data['total'] = total
        data['percentage'] = int((current / total * 100)) if total > 0 else 0
        data['updated_at'] = time.time()

        if message:
            data['message'] = message

        with open(progress_file, 'w') as f:
            json.dump(data, f)

    def get_progress(self, task_id: str) -> Optional[Dict]:
        """Get progress for a task."""
        progress_file = os.path.join(self.progress_dir, f"{task_id}.json")

        if not os.path.exists(progress_file):
            return None

        with open(progress_file, 'r') as f:
            return json.load(f)

    def complete_task(self, task_id: str, message: str = "Completed") -> None:
        """Mark a task as completed."""
        progress_file = os.path.join(self.progress_dir, f"{task_id}.json")

        if not os.path.exists(progress_file):
            return

        with open(progress_file, 'r') as f:
            data = json.load(f)

        data['status'] = 'completed'
        data['message'] = message
        data['percentage'] = 100
        data['updated_at'] = time.time()

        with open(progress_file, 'w') as f:
            json.dump(data, f)

    def fail_task(self, task_id: str, error_message: str) -> None:
        """Mark a task as failed."""
        progress_file = os.path.join(self.progress_dir, f"{task_id}.json")

        if not os.path.exists(progress_file):
            return

        with open(progress_file, 'r') as f:
            data = json.load(f)

        data['status'] = 'failed'
        data['message'] = error_message
        data['updated_at'] = time.time()

        with open(progress_file, 'w') as f:
            json.dump(data, f)

    def cleanup_task(self, task_id: str) -> None:
        """Remove progress file for a task."""
        progress_file = os.path.join(self.progress_dir, f"{task_id}.json")

        if os.path.exists(progress_file):
            os.remove(progress_file)
