"""Serialization of Python arguments into the API's query string (not public API).

Format, confirmed against the spec and the live API (``docs/api-notes.md``, "Array parameters
in query filters"):

- a list is one parameter with comma-separated values: ``f[types]=TV,WEB``, ``ids=1,2``;
- nested filters use bracketed keys: ``f[years][from_year]=2020``;
- a value that is ``None`` (or an empty list/dict) is left out entirely.

``bool`` is rejected rather than guessed: the spec has no boolean query parameters, so the
API's format for them (``1``/``true``/...) is unknown.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping, Sequence
from typing import Any


def build_query(params: Mapping[str, Any]) -> dict[str, str]:
    """Flatten ``params`` into query parameters as the API expects them.

    Args:
        params: Parameter names to values. A value can be ``None`` (skipped), a ``str``,
            ``int``, ``float`` or ``Enum`` (sent as its ``value``), a list/tuple of
            those (comma-joined), or a mapping (each key becomes a bracketed sub-key).

    Returns:
        Query parameters ready for ``httpx``.

    Raises:
        ValueError: A list item contains a comma — it would split into two values.
        TypeError: A value has an unsupported type (including ``bool``).

    Example:
        ```python
        build_query({"f": {"genres": [1, 5], "years": {"from_year": 2020}}, "page": 2})
        # {"f[genres]": "1,5", "f[years][from_year]": "2020", "page": "2"}
        ```
    """
    query: dict[str, str] = {}
    for name, value in params.items():
        _add(query, name, value)
    return query


def _add(query: dict[str, str], key: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, Mapping):
        for sub_key, sub_value in value.items():
            _add(query, f"{key}[{sub_key}]", sub_value)
        return
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        items = [_scalar(key, item) for item in value if item is not None]
        for item in items:
            if "," in item:
                raise ValueError(f"{key}: list item {item!r} contains a comma")
        if items:
            query[key] = ",".join(items)
        return
    query[key] = _scalar(key, value)


def _scalar(key: str, value: Any) -> str:
    if isinstance(value, enum.Enum):
        value = value.value
    if isinstance(value, str | int | float) and not isinstance(value, bool):
        return str(value)
    raise TypeError(f"{key}: unsupported query value {value!r} of type {type(value).__name__}")
