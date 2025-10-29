"""
Application Configuration Module
Centralized configuration management for Fortune Lab.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Application configuration with environment variable support."""

    # Flask Configuration
    SECRET_KEY: str = os.environ.get(
        "SECRET_KEY", "fortune-lab-secret-key-2024-change-in-production"
    )
    DEBUG: bool = os.environ.get("DEBUG", "True").lower() == "true"
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "5000"))
    TESTING: bool = os.environ.get("TESTING", "False").lower() == "true"

    # Data Paths
    DATA_PATH: str = os.environ.get("DATA_PATH", "app/data")
    ANALYSIS_PATH: str = os.environ.get(
        "ANALYSIS_PATH", "app/data/analysis"
    )
    PROGRESS_PATH: str = os.environ.get(
        "PROGRESS_PATH", "app/data/progress"
    )
    ACCURACY_PATH: str = os.environ.get(
        "ACCURACY_PATH", "app/data/accuracy"
    )

    # Scraper Configuration
    HEADLESS: bool = os.environ.get("HEADLESS", "True").lower() == "true"
    PCSO_URL: str = os.environ.get(
        "PCSO_URL", "https://www.pcso.gov.ph/SearchLottoResult.aspx"
    )
    PAGE_TIMEOUT: int = int(os.environ.get("PAGE_TIMEOUT", "30"))
    MAX_RETRIES: int = int(os.environ.get("MAX_RETRIES", "3"))

    # Progress Tracking
    PROGRESS_CLEANUP_AGE: int = int(
        os.environ.get("PROGRESS_CLEANUP_AGE", "300")
    )  # 5 minutes
    PROGRESS_POLL_INTERVAL: int = int(
        os.environ.get("PROGRESS_POLL_INTERVAL", "2")
    )  # 2 seconds

    # Logging Configuration
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.environ.get("LOG_FILE", "app.log")
    LOG_MAX_BYTES: int = int(
        os.environ.get("LOG_MAX_BYTES", "10485760")
    )  # 10MB
    LOG_BACKUP_COUNT: int = int(os.environ.get("LOG_BACKUP_COUNT", "5"))

    # Analysis Configuration
    DEFAULT_PREDICTION_COUNT: int = int(
        os.environ.get("DEFAULT_PREDICTION_COUNT", "5")
    )
    CACHE_ENABLED: bool = os.environ.get("CACHE_ENABLED", "True").lower() == "true"
    CACHE_TTL: int = int(os.environ.get("CACHE_TTL", "3600"))  # 1 hour

    # Default Date Range
    DEFAULT_START_YEAR: int = int(os.environ.get("DEFAULT_START_YEAR", "2015"))
    DEFAULT_START_MONTH: int = int(os.environ.get("DEFAULT_START_MONTH", "1"))
    DEFAULT_START_DAY: int = int(os.environ.get("DEFAULT_START_DAY", "1"))

    # Rate Limiting (Future)
    RATE_LIMIT_ENABLED: bool = (
        os.environ.get("RATE_LIMIT_ENABLED", "False").lower() == "true"
    )
    RATE_LIMIT_SCRAPE: str = os.environ.get("RATE_LIMIT_SCRAPE", "10 per hour")
    RATE_LIMIT_ANALYZE: str = os.environ.get("RATE_LIMIT_ANALYZE", "100 per hour")
    RATE_LIMIT_GENERAL: str = os.environ.get("RATE_LIMIT_GENERAL", "200 per hour")

    # Feature Flags
    ENABLE_WEBSOCKET: bool = (
        os.environ.get("ENABLE_WEBSOCKET", "False").lower() == "true"
    )
    ENABLE_API_DOCS: bool = (
        os.environ.get("ENABLE_API_DOCS", "True").lower() == "true"
    )
    ENABLE_METRICS: bool = (
        os.environ.get("ENABLE_METRICS", "False").lower() == "true"
    )

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Ensure required directories exist
        os.makedirs(self.DATA_PATH, exist_ok=True)
        os.makedirs(self.ANALYSIS_PATH, exist_ok=True)
        os.makedirs(self.PROGRESS_PATH, exist_ok=True)
        os.makedirs(self.ACCURACY_PATH, exist_ok=True)

        # Validate port range
        if not (1 <= self.PORT <= 65535):
            raise ValueError(f"Invalid PORT: {self.PORT}. Must be between 1 and 65535.")

        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.LOG_LEVEL.upper() not in valid_log_levels:
            raise ValueError(
                f"Invalid LOG_LEVEL: {self.LOG_LEVEL}. "
                f"Must be one of: {', '.join(valid_log_levels)}"
            )

    @property
    def flask_config(self) -> dict:
        """Get Flask-specific configuration as dictionary."""
        return {
            "SECRET_KEY": self.SECRET_KEY,
            "DEBUG": self.DEBUG,
            "TESTING": self.TESTING,
            "DATA_PATH": self.DATA_PATH,
        }

    def get_log_config(self) -> dict:
        """Get logging configuration."""
        return {
            "level": self.LOG_LEVEL,
            "file": self.LOG_FILE,
            "max_bytes": self.LOG_MAX_BYTES,
            "backup_count": self.LOG_BACKUP_COUNT,
        }

    def __repr__(self) -> str:
        """String representation (masks sensitive values)."""
        safe_attrs = {
            k: "***MASKED***" if "SECRET" in k.upper() or "KEY" in k.upper() else v
            for k, v in self.__dict__.items()
        }
        return f"Config({safe_attrs})"


# Global configuration instance
config = Config()


# Convenience function to reload configuration
def reload_config():
    """Reload configuration from environment variables."""
    global config
    config = Config()
    return config
