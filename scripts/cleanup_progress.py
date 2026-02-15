#!/usr/bin/env python
"""
Manual Progress Cleanup Utility
Run this script to clean up old/stale progress files manually.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.modules.progress_tracker import ProgressTracker
from app.config import config


def main():
    """Main cleanup function."""
    print("Progress Cleanup Utility")
    print("=" * 50)

    tracker = ProgressTracker(progress_dir=config.PROGRESS_PATH)

    # Show current progress files
    progress_dir = config.PROGRESS_PATH
    if os.path.exists(progress_dir):
        files = [f for f in os.listdir(progress_dir) if f.endswith(".json")]
        print(f"\nFound {len(files)} progress file(s)")

        if files:
            print("\nCurrent progress files:")
            for filename in files:
                filepath = os.path.join(progress_dir, filename)
                file_size = os.path.getsize(filepath)
                print(f"  - {filename} ({file_size} bytes)")
    else:
        print("\nNo progress directory found")
        return

    print("\n" + "=" * 50)
    print("Running cleanup...")
    print("=" * 50)

    # Run comprehensive cleanup
    results = tracker.cleanup_all()

    print("\nCleanup Results:")
    print(f"  Completed tasks cleaned: {results['completed_cleaned']}")
    print(f"  Stale tasks cleaned: {results['stale_cleaned']}")
    print(f"  Old tasks cleaned: {results['old_cleaned']}")
    print(f"  Total cleaned: {results['total_cleaned']}")

    # Show remaining files
    if os.path.exists(progress_dir):
        remaining_files = [f for f in os.listdir(progress_dir) if f.endswith(".json")]
        print(f"\nRemaining: {len(remaining_files)} progress file(s)")

    print("\n✓ Cleanup complete!")


if __name__ == "__main__":
    main()
