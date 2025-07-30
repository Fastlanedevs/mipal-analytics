from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


def pydantic_to_dict(
    obj: Any,
    exclude_none: bool = True,
    exclude_defaults: bool = False,
    exclude_unset: bool = False,
) -> Any:
    """
    Recursively converts a Pydantic model to a dictionary, properly handling nested models
    and various data types.

    Args:
        obj: The Pydantic model or any other object to convert
        exclude_none: If True, exclude fields with None values
        exclude_defaults: If True, exclude fields that have their default values
        exclude_unset: If True, exclude fields that were not explicitly set

    Returns:
        Dict[str, Any]: A dictionary representation of the object
    """
    if isinstance(obj, dict):
        return {
            key: pydantic_to_dict(value, exclude_none, exclude_defaults, exclude_unset)
            for key, value in obj.items()
            if not (exclude_none and value is None)
        }

    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj

    if isinstance(obj, datetime):
        return str(obj)

    if isinstance(obj, Enum):
        return obj.value

    if isinstance(obj, (list, set, tuple)):
        return [
            pydantic_to_dict(item, exclude_none, exclude_defaults, exclude_unset)
            for item in obj
        ]

    if isinstance(obj, BaseModel):
        # Get the model's dictionary representation with desired exclusions
        obj_dict = obj.model_dump(
            exclude_none=exclude_none,
            exclude_defaults=exclude_defaults,
            exclude_unset=exclude_unset,
            mode="json",  # This ensures Enums are converted to their values
        )
        # Recursively convert any nested objects
        return {
            key: pydantic_to_dict(value, exclude_none, exclude_defaults, exclude_unset)
            for key, value in obj_dict.items()
        }

    # Handle any other types by converting to string
    return str(obj)
