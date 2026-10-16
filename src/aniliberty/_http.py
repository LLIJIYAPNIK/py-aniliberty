"""Low-level HTTP client for the AniLibria API (exposed as ``AniLiberty.http``)."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, NoReturn

import httpx

from aniliberty._version import __version__
from aniliberty.exceptions import (
    AccessBlockedError,
    APIError,
    AuthRequiredError,
    NotFoundError,
    RateLimitError,
    ResponseParseError,
    ServerError,
    TransportError,
    ValidationError,
)

DEFAULT_BASE_URL = "https://aniliberty.top/api/v1"
"""The API's main server, as named by the OpenAPI spec and ``GET /app/status``.

``https://anilibria.top/api/v1`` serves the same API and works as a mirror (see
``docs/api-notes.md``).
"""

DEFAULT_TIMEOUT = 30.0
"""Default per-request timeout, in seconds."""

DEFAULT_HEADERS: dict[str, str] = {
    "Accept": "application/json",
    "User-Agent": f"py-aniliberty/{__version__} (+https://github.com/LLIJIYAPNIK/py-aniliberty)",
}
"""Headers sent with every request.

``Accept: application/json`` is required, not cosmetic: without it the API's Laravel backend
renders errors (404 at least) as HTML pages instead of JSON — see ``docs/api-notes.md``.
"""

logger = logging.getLogger("aniliberty")


class HttpClient:
    """Sends requests to the API and turns responses into JSON or SDK exceptions.

    Every resource of ``AniLiberty`` goes through this class; it is also the escape hatch for
    endpoints the SDK doesn't cover yet: ``await client.http.request("GET", "/teams/roles")``
    returns the decoded JSON as is, with the same headers and error handling as the rest of
    the SDK.

    Request paths are relative to ``base_url`` and joined as strings, so
    ``"/app/status"`` with the default base URL becomes
    ``https://aniliberty.top/api/v1/app/status``. Absolute URLs are not accepted.
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        headers: Mapping[str, str] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: API base URL including the version prefix, e.g.
                ``"https://anilibria.top/api/v1"`` for the mirror.
            timeout: Per-request timeout, in seconds. Ignored when ``http_client`` is given —
                that client's own timeout applies.
            headers: Extra headers merged over ``DEFAULT_HEADERS``; a key given here replaces
                the default one, matched case-insensitively. Overriding ``Accept`` breaks
                error handling (see ``DEFAULT_HEADERS``) — only do it knowingly.
            http_client: A ready ``httpx.AsyncClient`` to send requests with (custom
                transport, proxy, limits, ...). The SDK's headers are added to each request
                on top of the client's own, and the client is **not** closed by ``aclose()``
                — its owner is responsible for that.
        """
        self._base_url = base_url.rstrip("/")
        self._headers = httpx.Headers(DEFAULT_HEADERS)
        if headers is not None:
            self._headers.update(headers)
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=timeout)
        self._closed = False

    @property
    def base_url(self) -> str:
        """The API base URL, without a trailing slash."""
        return self._base_url

    @property
    def closed(self) -> bool:
        """Whether ``aclose()`` has been called."""
        return self._closed

    async def aclose(self) -> None:
        """Close the underlying ``httpx.AsyncClient``, unless it was passed in by the caller.

        Safe to call more than once.
        """
        if self._closed:
            return
        self._closed = True
        if self._owns_client:
            await self._client.aclose()

    def url(self, path: str) -> str:
        """Return the full URL for an API ``path`` such as ``"/app/status"``."""
        return f"{self._base_url}/{path.lstrip('/')}"

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        """Send a request and return the decoded JSON body.

        Args:
            method: HTTP method, e.g. ``"GET"``.
            path: Path relative to ``base_url``, e.g. ``"/anime/releases/latest"``.
            params: Query parameters, passed to ``httpx`` as is.
            json: JSON request body.

        Returns:
            The decoded JSON body (``dict``, ``list``, ...), or ``None`` for an empty body.

        Raises:
            APIError: The API answered with an error status — one of its subclasses for
                404, 422, 429, 401/403, 5xx and HTML pages.
            TransportError: The request failed without a response (network error, timeout).
            ResponseParseError: A successful response wasn't valid JSON.
            RuntimeError: The client has been closed.

        Example:
            ```python
            roles = await client.http.request("GET", "/teams/roles")
            ```
        """
        if self._closed:
            raise RuntimeError("This client has been closed; create a new AniLiberty instance.")
        method = method.upper()
        url = self.url(path)
        try:
            response = await self._client.request(
                method, url, params=params, json=json, headers=self._headers
            )
        except httpx.TransportError as exc:
            logger.debug("%s %s failed: %r", method, url, exc)
            raise TransportError(
                f"Request failed: {type(exc).__name__}: {exc}", method=method, url=url
            ) from exc
        logger.debug("%s %s -> %d", method, response.request.url, response.status_code)
        return _handle_response(response)


def _handle_response(response: httpx.Response) -> Any:
    """Return the decoded JSON body of a successful response, or raise the matching error."""
    method = response.request.method
    url = str(response.request.url)
    if _media_type(response) == "text/html" and not response.is_server_error:
        raise AccessBlockedError(
            "Got an HTML page instead of JSON: the request was likely stopped by the "
            "anti-bot protection in front of the API. Retrying won't help; if the API opens "
            "in a browser on this network, try a mirror via base_url=...",
            status_code=response.status_code,
            method=method,
            url=url,
            payload=response.text,
        )
    if response.is_success:
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:  # json.JSONDecodeError and UnicodeDecodeError
            raise ResponseParseError(
                "Response body is not valid JSON", url=url, payload=response.text
            ) from exc
    _raise_for_error(response, method=method, url=url)


def _raise_for_error(response: httpx.Response, *, method: str, url: str) -> NoReturn:
    payload = _decode_error_body(response)
    status = response.status_code
    api_message = payload.get("message") if isinstance(payload, dict) else None
    message = api_message if isinstance(api_message, str) else response.reason_phrase
    common: dict[str, Any] = {
        "status_code": status,
        "method": method,
        "url": url,
        "payload": payload,
    }
    if status == 404:
        raise NotFoundError("Not found", **common)
    if status == 422:
        errors = _validation_errors(payload)
        details = "; ".join(f"{field}: {' '.join(msgs)}" for field, msgs in errors.items())
        raise ValidationError(details or message, errors=errors, **common)
    if status == 429:
        raise RateLimitError(message, retry_after=_retry_after(response), **common)
    if status in (401, 403):
        raise AuthRequiredError(message, **common)
    if response.is_server_error:
        raise ServerError(message, **common)
    raise APIError(message, **common)


def _decode_error_body(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def _validation_errors(payload: Any) -> dict[str, list[str]]:
    """Extract ``{"errors": {field: [message, ...]}}`` from a 422 body, tolerating odd shapes."""
    errors = payload.get("errors") if isinstance(payload, dict) else None
    if not isinstance(errors, dict):
        return {}
    return {
        str(field): [str(m) for m in msgs] if isinstance(msgs, list) else [str(msgs)]
        for field, msgs in errors.items()
    }


def _media_type(response: httpx.Response) -> str:
    content_type: str = response.headers.get("Content-Type", "")
    return content_type.split(";")[0].strip().lower()


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


__all__ = ["DEFAULT_BASE_URL", "DEFAULT_HEADERS", "DEFAULT_TIMEOUT", "HttpClient"]
