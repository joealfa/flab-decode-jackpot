"""Isolated application fixtures with no browser or model dependencies."""

from pathlib import Path

import pytest

from app import create_app
from app.config import Config
from app.storage import write_json


@pytest.fixture
def settings(tmp_path: Path) -> Config:
    """Provide explicit local settings independent of environment credentials."""
    return Config(
        HOST="127.0.0.1",
        DEBUG=False,
        TESTING=True,
        BASIC_AUTH_USERNAME="",
        BASIC_AUTH_PASSWORD="",
        SSL_CERTFILE="",
        SSL_KEYFILE="",
        DATA_PATH=str(tmp_path),
        ANALYSIS_PATH="",
        AI_ANALYSIS_PATH="",
        ACCURACY_PATH="",
        PROGRESS_PATH="",
        RATE_LIMIT_ENABLED=False,
        RATE_LIMIT_STORAGE_URI="memory://",
    )


@pytest.fixture
def application(settings):
    """Create an app without a running scheduler."""
    return create_app(settings)


@pytest.fixture
def client(application):
    """Return a Flask client scoped to a temporary dataset."""
    return application.test_client()


@pytest.fixture
def result_file(settings):
    """Create a minimal known result file in temporary storage."""
    filename = "result_Lotto_6-42_20261101.json"
    write_json(
        Path(settings.DATA_PATH) / filename,
        {
            "game_type": "Lotto 6/42",
            "start_date": "2026-11-01",
            "end_date": "2026-11-01",
            "total_draws": 1,
            "results": [
                {
                    "date": "11/01/2026",
                    "numbers": [1, 2, 3, 4, 5, 6],
                    "day_of_week": "Sunday",
                    "winners": "0",
                    "jackpot": "N/A",
                }
            ],
        },
    )
    return filename
