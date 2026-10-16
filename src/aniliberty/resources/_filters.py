"""Validation of list/enum filters shared by the catalog and the account lists (not public API).

The API silently ignores (or answers nothing to) filter values it doesn't know, so they're
checked against the spec's enums before sending.
"""

from __future__ import annotations

from collections.abc import Sequence

from aniliberty.models.common import ValueDescription
from aniliberty.models.genre import Genre


def enum_values(
    name: str, values: Sequence[str | ValueDescription[str]] | None, allowed: tuple[str, ...]
) -> list[str] | None:
    """Turn ``values`` (strings or reference items) into strings the API knows, or raise."""
    if values is None:
        return None
    if isinstance(values, str):
        raise TypeError(f"{name} must be a list, e.g. {name}=[{values!r}]")
    return [enum_value(name, item, allowed) for item in values]


def enum_value(name: str, item: str | ValueDescription[str], allowed: tuple[str, ...]) -> str:
    """Turn one string or reference item into a string the API knows, or raise."""
    value = item.value if isinstance(item, ValueDescription) else item
    if value not in allowed:
        raise ValueError(f"Unknown {name} value {value!r}; expected one of: {', '.join(allowed)}")
    return value


def genre_ids(genres: Sequence[int | Genre] | None) -> list[int] | None:
    """Turn genre IDs or ``Genre`` objects into IDs, or raise."""
    if genres is None:
        return None
    ids = []
    for genre in genres:
        genre_id = genre.id if isinstance(genre, Genre) else genre
        if isinstance(genre_id, bool) or not isinstance(genre_id, int):
            raise TypeError(f"genres must be genre IDs or Genre objects, got {genre!r}")
        ids.append(genre_id)
    return ids
