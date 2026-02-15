"""
Input Validation Layer for Fortune Lab
Centralized validation functions for all API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.exceptions import (
    BadRequestException,
    InvalidDateRangeException,
    InvalidGameTypeException,
    InvalidNumbersException,
)

# Supported lottery games and their max numbers
VALID_GAME_TYPES = [
    "Lotto 6/42",
    "Mega Lotto 6/45",
    "Super Lotto 6/49",
    "Grand Lotto 6/55",
    "Ultra Lotto 6/58",
]

# Map game type to max number for number range validation
GAME_MAX_NUMBERS = {
    "Lotto 6/42": 42,
    "Mega Lotto 6/45": 45,
    "Super Lotto 6/49": 49,
    "Grand Lotto 6/55": 55,
    "Ultra Lotto 6/58": 58,
}

NUMBERS_PER_DRAW = 6


def require_json_body(data: Any) -> Dict:
    """Validate that the request body is valid JSON.

    Args:
        data: The parsed JSON body from request.get_json().

    Returns:
        The validated data dictionary.

    Raises:
        BadRequestException: If the body is missing or not a dictionary.
    """
    if not data or not isinstance(data, dict):
        raise BadRequestException("Request body must be JSON")
    return data


def require_fields(data: Dict, fields: List[str]) -> None:
    """Validate that all required fields are present and non-empty.

    Args:
        data: The request data dictionary.
        fields: List of required field names.

    Raises:
        BadRequestException: If any required field is missing.
    """
    missing = [f for f in fields if not data.get(f)]
    if missing:
        raise BadRequestException(
            "Missing required fields",
            details={
                "required": fields,
                "missing": missing,
                "provided": list(data.keys()),
            },
        )


def validate_game_type(game_type: str) -> str:
    """Validate that the game type is a supported PCSO lottery game.

    Args:
        game_type: The game type string to validate.

    Returns:
        The validated game type string.

    Raises:
        InvalidGameTypeException: If the game type is not valid.
    """
    if game_type not in VALID_GAME_TYPES:
        raise InvalidGameTypeException(game_type, VALID_GAME_TYPES)
    return game_type


def parse_date(date_str: str, field_name: str = "date") -> datetime:
    """Parse a date string in YYYY-MM-DD format.

    Args:
        date_str: The date string to parse.
        field_name: Name of the field for error messages.

    Returns:
        Parsed datetime object.

    Raises:
        BadRequestException: If the date format is invalid.
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError, TypeError:
        raise BadRequestException(
            f"Invalid {field_name} format. Use YYYY-MM-DD",
            details={field_name: date_str},
        )


def validate_date_range(start_date: datetime, end_date: datetime) -> None:
    """Validate that start_date is before or equal to end_date.

    Args:
        start_date: The start date.
        end_date: The end date.

    Raises:
        InvalidDateRangeException: If start_date is after end_date.
    """
    if start_date > end_date:
        raise InvalidDateRangeException(
            "Start date must be before or equal to end date",
            details={
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
            },
        )


def validate_lottery_numbers(
    numbers: Any, game_type: Optional[str] = None
) -> List[int]:
    """Validate lottery numbers for a draw submission.

    Args:
        numbers: The numbers to validate (expected: list of 6 integers).
        game_type: Optional game type to validate number range.

    Returns:
        Sorted list of validated integer numbers.

    Raises:
        InvalidNumbersException: If numbers are invalid.
    """
    if not isinstance(numbers, list):
        raise InvalidNumbersException(
            numbers if isinstance(numbers, list) else [],
            f"Numbers must be a list, got {type(numbers).__name__}",
        )

    if len(numbers) != NUMBERS_PER_DRAW:
        raise InvalidNumbersException(
            numbers,
            f"Must provide exactly {NUMBERS_PER_DRAW} numbers, got {len(numbers)}",
        )

    # Validate each number is an integer
    validated = []
    for i, n in enumerate(numbers):
        try:
            num = int(n)
        except ValueError, TypeError:
            raise InvalidNumbersException(
                numbers, f"Number at position {i + 1} is not a valid integer: {n}"
            )
        validated.append(num)

    # Validate range if game type is provided
    if game_type and game_type in GAME_MAX_NUMBERS:
        max_num = GAME_MAX_NUMBERS[game_type]
        out_of_range = [n for n in validated if n < 1 or n > max_num]
        if out_of_range:
            raise InvalidNumbersException(
                numbers,
                f"Numbers must be between 1 and {max_num} for {game_type}. "
                f"Out of range: {out_of_range}",
            )

    # Check for duplicates
    if len(set(validated)) != len(validated):
        duplicates = [n for n in validated if validated.count(n) > 1]
        raise InvalidNumbersException(
            numbers, f"Duplicate numbers not allowed: {list(set(duplicates))}"
        )

    return sorted(validated)


def validate_cleanup_strategy(strategy: str) -> str:
    """Validate cleanup strategy parameter.

    Args:
        strategy: The cleanup strategy string.

    Returns:
        The validated strategy string.

    Raises:
        BadRequestException: If the strategy is not valid.
    """
    valid_strategies = ["all", "completed", "stale", "old"]
    if strategy not in valid_strategies:
        raise BadRequestException(
            f"Invalid cleanup strategy: {strategy}",
            details={"valid_strategies": valid_strategies},
        )
    return strategy


def game_type_to_slug(game_type: str) -> str:
    """Convert a game type to its filename slug format.

    Args:
        game_type: The game type (e.g., "Lotto 6/42").

    Returns:
        The slug (e.g., "Lotto_6-42").
    """
    return game_type.replace(" ", "_").replace("/", "-")
