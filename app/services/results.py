"""Draw submission operations independent of HTTP requests."""

from datetime import datetime
from typing import Any

from app.exceptions import BadRequestException
from app.storage import update_json


def submit_draw(
    filepath: str, game_type: str, draw: dict[str, Any]
) -> tuple[dict, bool]:
    """Validate and update a dataset under a single file transaction.

    Args:
        filepath: Contained result file path.
        game_type: Validated lottery game.
        draw: Validated draw entry.

    Returns:
        Updated dataset and whether an existing draw was replaced.

    Raises:
        BadRequestException: If the selected dataset is invalid or mismatched.
    """

    def mutate(data: Any) -> tuple[dict, bool]:
        """Apply a draw while the repository holds its lock."""
        if (
            not isinstance(data, dict)
            or data.get("game_type") != game_type
            or not isinstance(data.get("results"), list)
        ):
            raise BadRequestException("Selected result file has an invalid format")
        existing = next(
            (
                index
                for index, item in enumerate(data["results"])
                if item["date"] == draw["date"]
            ),
            None,
        )
        if existing is None:
            data["results"].append(draw)
        else:
            data["results"][existing] = draw
        data["results"].sort(
            key=lambda item: datetime.strptime(item["date"], "%m/%d/%Y"), reverse=True
        )
        data["total_draws"] = len(data["results"])
        draw_day = datetime.strptime(draw["date"], "%m/%d/%Y").strftime("%Y-%m-%d")
        data["start_date"] = min(data.get("start_date", draw_day), draw_day)
        data["end_date"] = max(data.get("end_date", draw_day), draw_day)
        return data, existing is not None

    return update_json(filepath, mutate)
