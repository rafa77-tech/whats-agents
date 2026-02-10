"""
Sprint 44 T01.4: Utility functions for safe data access.

Provides helper functions to avoid common IndexError and KeyError issues
when working with database results and API responses.
"""

from typing import Any, Optional, TypeVar

T = TypeVar("T")


def safe_first(result: Any) -> Optional[dict]:
    """
    Safely get the first item from a Supabase query result.

    Avoids IndexError when accessing .data[0] on empty results.

    Args:
        result: Supabase query result with .data attribute

    Returns:
        First item dict or None if empty/invalid

    Example:
        # Before (unsafe):
        if result.data:
            item = result.data[0]  # IndexError if data is []

        # After (safe):
        item = safe_first(result)
        if not item:
            return {"error": "Not found"}
    """
    if result is None:
        return None

    # Handle Supabase result objects
    if hasattr(result, "data"):
        data = result.data
        if data and len(data) > 0:
            return data[0]
        return None

    # Handle raw lists
    if isinstance(result, list):
        if len(result) > 0:
            return result[0]
        return None

    return None


def safe_get(data: Optional[dict], key: str, default: T = None) -> T:
    """
    Safely get a value from a dict that might be None.

    Args:
        data: Dict or None
        key: Key to retrieve
        default: Default value if key not found or data is None

    Returns:
        Value or default

    Example:
        # Before (unsafe):
        value = response.data[0].get("key")  # KeyError if data is None

        # After (safe):
        item = safe_first(response)
        value = safe_get(item, "key", "default")
    """
    if data is None:
        return default
    return data.get(key, default)


def safe_first_field(result: Any, field: str, default: T = None) -> T:
    """
    Safely get a field from the first item of a query result.

    Combines safe_first and safe_get in one call.

    Args:
        result: Supabase query result
        field: Field name to retrieve
        default: Default value if not found

    Returns:
        Field value or default

    Example:
        # Before (unsafe):
        hospital_id = result.data[0]["hospital_id"]

        # After (safe):
        hospital_id = safe_first_field(result, "hospital_id")
    """
    item = safe_first(result)
    return safe_get(item, field, default)
