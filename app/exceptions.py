"""
Custom Exceptions for Fortune Lab
Provides a hierarchy of exceptions for better error handling and debugging.
"""


class FortuneLabException(Exception):
    """Base exception for all Fortune Lab errors."""

    def __init__(self, message: str, details: dict = None):
        """
        Initialize exception with message and optional details.

        Args:
            message: Error message
            details: Optional dictionary with additional error context
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for JSON responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


# Scraper Exceptions
class ScraperException(FortuneLabException):
    """Base exception for scraper-related errors."""
    pass


class WebDriverException(ScraperException):
    """WebDriver initialization or operation failed."""
    pass


class PCSOWebsiteException(ScraperException):
    """PCSO website access or navigation failed."""
    pass


class DataExtractionException(ScraperException):
    """Failed to extract data from PCSO website."""
    pass


class ScrapingTimeoutException(ScraperException):
    """Scraping operation timed out."""
    pass


class DateRangeException(ScraperException):
    """Requested date range is not available on PCSO website."""
    
    def __init__(self, message: str, requested_range: tuple = None, available_range: tuple = None):
        """
        Initialize with date range details.
        
        Args:
            message: Error message
            requested_range: Tuple of (start_year, end_year) requested
            available_range: Tuple of (min_year, max_year) available
        """
        details = {}
        if requested_range:
            details['requested_start_year'] = requested_range[0]
            details['requested_end_year'] = requested_range[1]
        if available_range:
            details['available_min_year'] = available_range[0]
            details['available_max_year'] = available_range[1]
        super().__init__(message, details)


# Analyzer Exceptions
class AnalyzerException(FortuneLabException):
    """Base exception for analyzer-related errors."""
    pass


class InsufficientDataException(AnalyzerException):
    """Not enough data to perform analysis."""
    pass


class AnalysisCalculationException(AnalyzerException):
    """Error during statistical calculation."""
    pass


class PredictionGenerationException(AnalyzerException):
    """Failed to generate predictions."""
    pass


# Data Exceptions
class DataException(FortuneLabException):
    """Base exception for data-related errors."""
    pass


class DataNotFoundException(DataException):
    """Data file or resource not found."""
    pass


class InvalidDataFormatException(DataException):
    """Data format is invalid or corrupted."""
    pass


class DataValidationException(DataException):
    """Data validation failed."""
    pass


class DataSerializationException(DataException):
    """Failed to serialize/deserialize data."""
    pass


# Validation Exceptions
class ValidationException(FortuneLabException):
    """Base exception for validation errors."""
    pass


class InvalidGameTypeException(ValidationException):
    """Invalid lottery game type specified."""

    def __init__(self, game_type: str, valid_types: list):
        super().__init__(
            f"Invalid game type: {game_type}",
            {"provided": game_type, "valid_types": valid_types},
        )


class DateRangeException(ValidationException):
    """Invalid date range specified."""
    pass


class InvalidInputException(ValidationException):
    """Invalid input parameters."""
    pass


class InvalidNumbersException(ValidationException):
    """Invalid lottery numbers."""

    def __init__(self, numbers: list, reason: str):
        super().__init__(
            f"Invalid numbers: {reason}",
            {"provided_numbers": numbers, "reason": reason},
        )


# Progress Tracking Exceptions
class ProgressException(FortuneLabException):
    """Base exception for progress tracking errors."""
    pass


class TaskNotFoundException(ProgressException):
    """Progress task not found."""
    pass


class TaskAlreadyExistsException(ProgressException):
    """Task already exists."""
    pass


# Configuration Exceptions
class ConfigurationException(FortuneLabException):
    """Base exception for configuration errors."""
    pass


class InvalidConfigurationException(ConfigurationException):
    """Configuration value is invalid."""
    pass


class MissingConfigurationException(ConfigurationException):
    """Required configuration is missing."""
    pass


# File System Exceptions
class FileSystemException(FortuneLabException):
    """Base exception for file system errors."""
    pass


class FilePermissionException(FileSystemException):
    """Insufficient permissions to access file."""
    pass


class DirectoryNotFoundException(FileSystemException):
    """Required directory not found."""
    pass


class FileWriteException(FileSystemException):
    """Failed to write file."""
    pass


# API Exceptions
class APIException(FortuneLabException):
    """Base exception for API errors."""

    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        """
        Initialize API exception with status code.

        Args:
            message: Error message
            status_code: HTTP status code
            details: Optional error details
        """
        super().__init__(message, details)
        self.status_code = status_code

    def to_response_dict(self) -> tuple:
        """Convert to Flask response format (dict, status_code)."""
        return (
            {
                "success": False,
                "error": self.message,
                "details": self.details,
                "error_type": self.__class__.__name__,
            },
            self.status_code,
        )


class BadRequestException(APIException):
    """Bad request (400)."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, 400, details)


class NotFoundException(APIException):
    """Resource not found (404)."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, 404, details)


class ConflictException(APIException):
    """Resource conflict (409)."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, 409, details)


class RateLimitException(APIException):
    """Rate limit exceeded (429)."""

    def __init__(self, message: str = "Rate limit exceeded", details: dict = None):
        super().__init__(message, 429, details)


class InternalServerException(APIException):
    """Internal server error (500)."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, 500, details)
