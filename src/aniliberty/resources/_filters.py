"""Argument checks shared by the catalog and the account lists (not public API).

The API silently ignores (or answers nothing to) filter values it doesn't know, so they're
checked against the spec's enums before sending.
"""

from __future__ import annotations

from collections.abc import Sequence

from aniliberty.models.common import ValueDescription
from aniliberty.models.genre import Genre
from aniliberty.models.release import Release


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


def year_list(years: Sequence[int] | None) -> list[int] | None:
    """Check a list of years (``range`` works too) and return it as a list, or raise."""
    if years is None:
        return None
    if not isinstance(years, Sequence) or isinstance(years, str):
        raise TypeError(f"years must be a list of years, e.g. years=[{years!r}]")
    for year in years:
        if isinstance(year, bool) or not isinstance(year, int):
            raise TypeError(f"years must be ints, got {year!r}")
    return list(years)


def release_ids(releases: Sequence[int | Release]) -> list[int]:
    """Turn release IDs or ``Release`` objects (at least one) into IDs, or raise."""
    if not releases:
        raise ValueError("Pass at least one release (an ID or a Release object)")
    ids = []
    for release in releases:
        release_id = release.id if isinstance(release, Release) else release
        if isinstance(release_id, bool) or not isinstance(release_id, int):
            raise TypeError(f"Expected a release ID or a Release, got {release!r}")
        ids.append(release_id)
    return ids
