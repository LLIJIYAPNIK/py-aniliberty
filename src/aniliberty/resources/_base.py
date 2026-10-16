"""Base class for resource namespaces such as ``client.app`` (not public API)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar, TypeVar

import pydantic

from aniliberty._http import HttpClient
from aniliberty._query import build_query
from aniliberty.exceptions import ResponseParseError

T = TypeVar("T")


class BaseResource:
    """A group of SDK methods mapping to one part of the API, sharing one ``HttpClient``.

    Attributes:
        ENDPOINTS: The spec operations this resource implements, as ``(METHOD, path)`` pairs
            spelled exactly as in ``spec/openapi.json``. Used to check that every operation
            of the spec is either implemented or explicitly skipped.
    """

    ENDPOINTS: ClassVar[tuple[tuple[str, str], ...]] = ()

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    async def _get(
        self, path: str, type_: type[T], *, params: Mapping[str, Any] | None = None
    ) -> T:
        """GET ``path`` and validate the JSON body as ``type_``.

        ``params`` go through ``build_query`` (lists → comma-joined, nested mappings →
        bracketed keys, ``None`` skipped). Validation runs with
        ``context={"site_url": ...}`` so images resolve to absolute URLs on the host the
        client talks to.
        """
        query = build_query(params) if params else None
        payload = await self._http.request("GET", path, params=query)
        try:
            return pydantic.TypeAdapter(type_).validate_python(
                payload, context={"site_url": self._http.site_url}
            )
        except pydantic.ValidationError as exc:
            raise ResponseParseError(
                f"Response doesn't match {getattr(type_, '__name__', type_)}: "
                f"{exc.error_count()} validation error(s)",
                url=self._http.url(path),
                payload=payload,
            ) from exc


def path_segment(value: int | str, *, what: str) -> str:
    """Check an ID or alias before it's put into a URL path, and return it as a string.

    Rejects values that would change which path is requested (``/``, ``.``, ``..``) or that
    are clearly not identifiers (empty strings, ``bool``, other types), so a bad argument
    fails here with a clear message instead of hitting some other endpoint.

    Args:
        value: The ID or alias.
        what: What the value is, for error messages (e.g. ``"release ID or alias"``).

    Raises:
        TypeError: ``value`` is not an ``int`` or ``str``.
        ValueError: ``value`` is empty or contains a path separator.
    """
    if isinstance(value, bool) or not isinstance(value, int | str):
        raise TypeError(f"Expected a {what}, got {value!r}")
    text = str(value)
    if not text or "/" in text or text in (".", ".."):
        raise ValueError(f"Invalid {what}: {value!r}")
    return text
