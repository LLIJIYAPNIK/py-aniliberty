"""Base class for resource namespaces such as ``client.app`` (not public API)."""

from __future__ import annotations

from typing import Any, ClassVar, TypeVar

import pydantic

from aniliberty._http import HttpClient
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

    async def _get(self, path: str, type_: type[T], *, params: dict[str, Any] | None = None) -> T:
        """GET ``path`` and validate the JSON body as ``type_``."""
        payload = await self._http.request("GET", path, params=params)
        try:
            return pydantic.TypeAdapter(type_).validate_python(payload)
        except pydantic.ValidationError as exc:
            raise ResponseParseError(
                f"Response doesn't match {getattr(type_, '__name__', type_)}: "
                f"{exc.error_count()} validation error(s)",
                url=self._http.url(path),
                payload=payload,
            ) from exc
