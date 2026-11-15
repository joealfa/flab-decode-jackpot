"""Scientific JSON normalization independent of the HTTP layer."""

from typing import Any

import numpy as np


def convert_to_serializable(value: Any) -> Any:
    """Recursively normalize scientific scalars and containers."""
    if isinstance(value, np.ndarray):
        return convert_to_serializable(value.tolist())
    if isinstance(value, np.generic):
        return convert_to_serializable(value.item())
    if isinstance(value, dict):
        return {key: convert_to_serializable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [convert_to_serializable(item) for item in value]
    return value
