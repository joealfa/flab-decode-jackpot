"""
Application Configuration Module
Centralized configuration management for Fortune Lab.
"""

import ipaddress
import os
import secrets
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from werkzeug.local import LocalProxy


@dataclass
class Config:
    """Application configuration with environment variable support."""

    # Flask Configuration
    SECRET_KEY: str = field(default_factory=lambda: os.environ.get("SECRET_KEY", ""))
    DEBUG: bool = field(
        default_factory=lambda: os.environ.get("DEBUG", "False").lower() == "true"
    )
    HOST: str = field(default_factory=lambda: os.environ.get("HOST", "127.0.0.1"))
    PORT: int = field(default_factory=lambda: int(os.environ.get("PORT", "5000")))
    TESTING: bool = field(
        default_factory=lambda: os.environ.get("TESTING", "False").lower() == "true"
    )
    BASIC_AUTH_USERNAME: str = field(
        default_factory=lambda: os.environ.get("BASIC_AUTH_USERNAME", "")
    )
    BASIC_AUTH_PASSWORD: str = field(
        default_factory=lambda: os.environ.get("BASIC_AUTH_PASSWORD", "")
    )
    SSL_CERTFILE: str = field(
        default_factory=lambda: os.environ.get("SSL_CERTFILE", "")
    )
    SSL_KEYFILE: str = field(default_factory=lambda: os.environ.get("SSL_KEYFILE", ""))

    # Data Paths
    DATA_PATH: str = field(
        default_factory=lambda: os.environ.get("DATA_PATH", "app/data")
    )
    ANALYSIS_PATH: str = field(
        default_factory=lambda: os.environ.get("ANALYSIS_PATH", "")
    )
    AI_ANALYSIS_PATH: str = field(
        default_factory=lambda: os.environ.get("AI_ANALYSIS_PATH", "")
    )
    PROGRESS_PATH: str = field(
        default_factory=lambda: os.environ.get("PROGRESS_PATH", "")
    )
    ACCURACY_PATH: str = field(
        default_factory=lambda: os.environ.get("ACCURACY_PATH", "")
    )

    # Scraper Configuration
    HEADLESS: bool = field(
        default_factory=lambda: os.environ.get("HEADLESS", "True").lower() == "true"
    )
    PCSO_URL: str = field(
        default_factory=lambda: os.environ.get(
            "PCSO_URL", "https://www.pcso.gov.ph/SearchLottoResult.aspx"
        )
    )
    PAGE_TIMEOUT: int = field(
        default_factory=lambda: int(os.environ.get("PAGE_TIMEOUT", "30"))
    )
    MAX_RETRIES: int = field(
        default_factory=lambda: int(os.environ.get("MAX_RETRIES", "3"))
    )

    # Progress Tracking
    PROGRESS_CLEANUP_AGE: int = field(
        default_factory=lambda: int(os.environ.get("PROGRESS_CLEANUP_AGE", "180"))
    )
    PROGRESS_POLL_INTERVAL: int = field(
        default_factory=lambda: int(os.environ.get("PROGRESS_POLL_INTERVAL", "2"))
    )

    # Logging Configuration
    LOG_LEVEL: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))

    # Analysis Configuration
    DEFAULT_PREDICTION_COUNT: int = field(
        default_factory=lambda: int(os.environ.get("DEFAULT_PREDICTION_COUNT", "5"))
    )
    CACHE_ENABLED: bool = field(
        default_factory=lambda: (
            os.environ.get("CACHE_ENABLED", "True").lower() == "true"
        )
    )
    CACHE_TTL: int = field(
        default_factory=lambda: int(os.environ.get("CACHE_TTL", "3600"))
    )

    # Default Date Range
    DEFAULT_START_YEAR: int = field(
        default_factory=lambda: int(os.environ.get("DEFAULT_START_YEAR", "2015"))
    )
    DEFAULT_START_MONTH: int = field(
        default_factory=lambda: int(os.environ.get("DEFAULT_START_MONTH", "1"))
    )
    DEFAULT_START_DAY: int = field(
        default_factory=lambda: int(os.environ.get("DEFAULT_START_DAY", "1"))
    )

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = field(
        default_factory=lambda: (
            os.environ.get("RATE_LIMIT_ENABLED", "True").lower() == "true"
        )
    )
    RATE_LIMIT_SCRAPE: str = field(
        default_factory=lambda: os.environ.get("RATE_LIMIT_SCRAPE", "10 per hour")
    )
    RATE_LIMIT_ANALYZE: str = field(
        default_factory=lambda: os.environ.get("RATE_LIMIT_ANALYZE", "100 per hour")
    )
    RATE_LIMIT_GENERAL: str = field(
        default_factory=lambda: os.environ.get("RATE_LIMIT_GENERAL", "200 per hour")
    )
    RATE_LIMIT_STORAGE_URI: str = field(
        default_factory=lambda: os.environ.get("RATE_LIMIT_STORAGE_URI", "memory://")
    )
    MAX_CONCURRENT_SCRAPES: int = field(
        default_factory=lambda: int(os.environ.get("MAX_CONCURRENT_SCRAPES", "1"))
    )

    # AI Configuration (Ollama)
    OLLAMA_ENABLED: bool = field(
        default_factory=lambda: (
            os.environ.get("OLLAMA_ENABLED", "True").lower() == "true"
        )
    )
    OLLAMA_MODEL: str = field(
        default_factory=lambda: os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
    )
    OLLAMA_HOST: str = field(
        default_factory=lambda: os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    )
    OLLAMA_TIMEOUT: int = field(
        default_factory=lambda: int(os.environ.get("OLLAMA_TIMEOUT", "300"))
    )

    # Feature Flags
    ENABLE_WEBSOCKET: bool = field(
        default_factory=lambda: (
            os.environ.get("ENABLE_WEBSOCKET", "False").lower() == "true"
        )
    )
    ENABLE_API_DOCS: bool = field(
        default_factory=lambda: (
            os.environ.get("ENABLE_API_DOCS", "True").lower() == "true"
        )
    )
    ENABLE_METRICS: bool = field(
        default_factory=lambda: (
            os.environ.get("ENABLE_METRICS", "False").lower() == "true"
        )
    )

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.SECRET_KEY:
            self.SECRET_KEY = secrets.token_hex(32)

        root = Path(__file__).resolve().parents[1]
        self.DATA_PATH = str((root / self.DATA_PATH).resolve())
        for attribute, child in (
            ("ANALYSIS_PATH", "analysis"),
            ("AI_ANALYSIS_PATH", "ai_analysis"),
            ("PROGRESS_PATH", "progress"),
            ("ACCURACY_PATH", "accuracy"),
        ):
            configured = getattr(self, attribute)
            setattr(
                self,
                attribute,
                str(
                    (
                        root / configured
                        if configured
                        else Path(self.DATA_PATH) / child
                    ).resolve()
                ),
            )

        if not (1 <= self.PORT <= 65535):
            raise ValueError(f"Invalid PORT: {self.PORT}. Must be between 1 and 65535.")

        if self.MAX_CONCURRENT_SCRAPES < 1:
            raise ValueError("MAX_CONCURRENT_SCRAPES must be at least 1.")

        if bool(self.BASIC_AUTH_USERNAME) != bool(self.BASIC_AUTH_PASSWORD):
            raise ValueError(
                "BASIC_AUTH_USERNAME and BASIC_AUTH_PASSWORD must be configured together."
            )

        host = self.HOST.strip().strip("[]").lower()
        try:
            is_loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            is_loopback = host == "localhost"

        if not is_loopback and not (
            self.BASIC_AUTH_USERNAME and self.BASIC_AUTH_PASSWORD
        ):
            raise ValueError(
                "Basic authentication credentials are required when HOST is not a loopback address."
            )

        if bool(self.SSL_CERTFILE) != bool(self.SSL_KEYFILE):
            raise ValueError(
                "SSL_CERTFILE and SSL_KEYFILE must be configured together."
            )
        if not is_loopback:
            if self.DEBUG:
                raise ValueError("DEBUG must be disabled for non-loopback hosts.")
            if not self.SSL_CERTFILE:
                raise ValueError(
                    "TLS certificates are required for non-loopback hosts."
                )
            if (
                not self.RATE_LIMIT_ENABLED
                or self.RATE_LIMIT_STORAGE_URI == "memory://"
            ):
                raise ValueError(
                    "Non-loopback hosts require enabled rate limits with shared storage."
                )
        for attribute in ("SSL_CERTFILE", "SSL_KEYFILE"):
            configured = getattr(self, attribute)
            if configured:
                path = (root / configured).resolve()
                if not path.is_file():
                    raise ValueError(f"{attribute} must reference an existing file.")
                setattr(self, attribute, str(path))

        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self.LOG_LEVEL = self.LOG_LEVEL.upper()
        if self.LOG_LEVEL not in valid_log_levels:
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
            "RATELIMIT_ENABLED": self.RATE_LIMIT_ENABLED,
            "RATELIMIT_STORAGE_URI": self.RATE_LIMIT_STORAGE_URI,
            "RATELIMIT_DEFAULT": self.RATE_LIMIT_GENERAL,
            "MAX_CONTENT_LENGTH": 1024 * 1024,
        }

    def get_log_config(self) -> dict:
        """Get logging configuration."""
        return {
            "level": self.LOG_LEVEL,
        }

    def __repr__(self) -> str:
        """String representation (masks sensitive values)."""
        safe_attrs = {
            k: "***MASKED***"
            if any(s in k.upper() for s in ("SECRET", "KEY", "PASSWORD", "TOKEN"))
            else v
            for k, v in self.__dict__.items()
        }
        return f"Config({safe_attrs})"


@cache
def get_config() -> Config:
    """Lazily load configuration for standalone domain module callers."""
    return Config()


config = LocalProxy(get_config)


# Convenience function to reload configuration
def reload_config() -> Config:
    """Reload configuration from environment variables."""
    get_config.cache_clear()
    return get_config()
