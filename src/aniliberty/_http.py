"""Low-level HTTP client for the AniLibria API (exposed as ``AniLiberty.http``)."""

from __future__ import annotations

import asyncio
import contextlib
import json as jsonlib
import logging
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, NoReturn

import httpx

from aniliberty._cache import DiskCache
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

DEFAULT_SITE_URL = "https://aniliberty.top"
"""Origin of ``DEFAULT_BASE_URL``: relative image paths in responses resolve against it."""

DEFAULT_TIMEOUT = 30.0
"""Default per-request timeout, in seconds."""

DEFAULT_MAX_CONCURRENCY = 5
"""Default maximum number of requests in flight at once."""

DEFAULT_REQUEST_DELAY = 0.1
"""Default minimum time, in seconds, between the starts of two consecutive requests."""

DEFAULT_MAX_RETRIES = 3
"""Default number of retries after the first attempt (so up to 4 attempts in total)."""

DEFAULT_RETRY_BASE_DELAY = 1.0
"""Default delay before the first retry, in seconds; doubled for every next one."""

DEFAULT_MAX_RETRY_AFTER = 60.0
"""Longest ``Retry-After``, in seconds, the client waits out; a longer one fails at once."""

DEFAULT_HEADERS: dict[str, str] = {
    "Accept": "application/json",
    "User-Agent": f"py-aniliberty/{__version__} (+https://github.com/LLIJIYAPNIK/py-aniliberty)",
}
"""Headers sent with every request.

``Accept: application/json`` is required, not cosmetic: without it the API's Laravel backend
renders errors (404 at least) as HTML pages instead of JSON — see ``docs/api-notes.md``.
"""

IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})
"""Methods that are safe to resend after a 5xx or a network error.

A 5xx or a dropped connection doesn't say whether the server already acted on the request, so
a ``POST`` (e.g. adding a release to favorites) is not resent then. 429 is retried for every
method: the server explicitly refused to process the request.
"""

logger = logging.getLogger("aniliberty")


class HttpClient:
    """Sends requests to the API and turns responses into JSON or SDK exceptions.

    Every resource of ``AniLiberty`` goes through this class; it is also the escape hatch for
    endpoints the SDK doesn't cover yet: ``await client.http.request("GET", "/teams/roles")``
    returns the decoded JSON as is, with the same headers, limits, retries and error handling
    as the rest of the SDK.

    Request paths are relative to ``base_url`` and joined as strings, so
    ``"/app/status"`` with the default base URL becomes
    ``https://aniliberty.top/api/v1/app/status``. Absolute URLs are not accepted.

    Being polite to the API is built in:

    - **Concurrency** — at most ``max_concurrency`` requests are in flight at once, however
      many coroutines call the client (e.g. via ``asyncio.gather``).
    - **Pacing** — consecutive requests start at least ``request_delay`` seconds apart.
    - **Retries** — 429 is retried for any method, 5xx and network errors/timeouts only for
      idempotent methods (``IDEMPOTENT_METHODS``). The delay is the response's
      ``Retry-After`` when it has one, otherwise ``retry_base_delay`` doubled per attempt
      (1 s, 2 s, 4 s by default). Other 4xx and HTML block pages are never retried.

    With ``cache_dir`` set, ``request(..., cache=True)`` keeps the decoded JSON of successful
    ``GET`` responses on disk and answers repeated identical requests from there until
    ``cache_ttl`` passes — see ``request()`` for what is and isn't cached.
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        headers: Mapping[str, str] | None = None,
        http_client: httpx.AsyncClient | None = None,
        token: str | None = None,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
        request_delay: float = DEFAULT_REQUEST_DELAY,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_base_delay: float = DEFAULT_RETRY_BASE_DELAY,
        max_retry_after: float = DEFAULT_MAX_RETRY_AFTER,
        cache_dir: str | os.PathLike[str] | None = None,
        cache_ttl: float | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
        cache_clock: Callable[[], float] = time.time,
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
            token: Session token sent as ``Authorization: Bearer <token>`` with every
                request; see the ``token`` property.
            max_concurrency: Maximum number of requests in flight at once.
            request_delay: Minimum time, in seconds, between the starts of two consecutive
                requests. ``0`` disables pacing.
            max_retries: How many times to retry a retryable failure before raising. ``0``
                disables retries.
            retry_base_delay: Delay before the first retry, in seconds, when the response
                has no ``Retry-After``; doubled for every next retry.
            max_retry_after: Longest ``Retry-After``, in seconds, worth waiting for. A 429
                asking for more raises ``RateLimitError`` right away instead of blocking.
            cache_dir: Directory for the response cache, created on the first write.
                ``None`` (the default) disables caching.
            cache_ttl: Seconds after which a cached response is stale and fetched again.
                ``None`` means cached responses never expire on their own. Ignored without
                ``cache_dir``.
            sleep: Async sleep function used for pacing and backoff. Replaceable in tests.
            clock: Monotonic time source used for pacing. Replaceable in tests.
            cache_clock: Wall-clock time source used to stamp and expire cache entries.
                Replaceable in tests.

        Raises:
            ValueError: A limit is out of range (``max_concurrency < 1`` or a negative
                delay, retry count or ``cache_ttl``).
        """
        if max_concurrency < 1:
            raise ValueError(f"max_concurrency must be at least 1, got {max_concurrency}")
        for name, value in (
            ("request_delay", request_delay),
            ("max_retries", max_retries),
            ("retry_base_delay", retry_base_delay),
            ("max_retry_after", max_retry_after),
        ):
            if value < 0:
                raise ValueError(f"{name} must not be negative, got {value}")
        self._base_url = base_url.rstrip("/")
        self._headers = httpx.Headers(DEFAULT_HEADERS)
        if headers is not None:
            self._headers.update(headers)
        self._token = token or None
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=timeout)
        self._closed = False
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._request_delay = request_delay
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay
        self._max_retry_after = max_retry_after
        self._sleep = sleep
        self._clock = clock
        self._pacing_lock = asyncio.Lock()
        self._last_request_at: float | None = None
        self._cache = (
            None if cache_dir is None else DiskCache(cache_dir, ttl=cache_ttl, clock=cache_clock)
        )

    @property
    def base_url(self) -> str:
        """The API base URL, without a trailing slash."""
        return self._base_url

    @property
    def site_url(self) -> str:
        """Origin of ``base_url`` (scheme and host), e.g. ``https://aniliberty.top``.

        Relative paths in responses, such as image paths, resolve against it.
        """
        url = httpx.URL(self._base_url)
        port = f":{url.port}" if url.port is not None else ""
        return f"{url.scheme}://{url.host}{port}"

    @property
    def cache_dir(self) -> Path | None:
        """The response cache directory, or ``None`` when caching is off."""
        return None if self._cache is None else self._cache.directory

    @property
    def token(self) -> str | None:
        """Session token sent as ``Authorization: Bearer <token>``, or ``None`` for none.

        Set it to start or stop sending the token; it replaces an ``Authorization`` header
        given in ``headers``. Public endpoints work with or without it (even with an expired
        one); account endpoints answer 403 without a valid one.
        """
        return self._token

    @token.setter
    def token(self, value: str | None) -> None:
        self._token = value or None

    def _discard_cookie(self, name: str) -> None:
        """Remove a cookie the API has set from the underlying client's cookie jar.

        Login responses also set the session token as the ``_al1`` cookie, which httpx
        keeps and sends back — and which authenticates on its own. The SDK authenticates
        with ``token`` only, so it drops that cookie to keep ``token`` the single source of
        truth.
        """
        self._client.cookies.delete(name)

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
        with_token: bool = True,
        cache: bool = False,
        refresh: bool = False,
    ) -> Any:
        """Send a request and return the decoded JSON body.

        Retries and limits described on the class apply.

        A response is read from and saved to the cache only when all of these hold: the
        client has a ``cache_dir``, ``cache=True``, the method is ``GET``, and no session
        token goes with the request — so nothing that depends on the logged-in user (or
        carries their torrent passkey) ever lands on disk. The cache key is the method, the
        full URL and the query parameters in sorted order. Only successful responses with a
        body are cached; errors are raised as usual and never stored.

        Args:
            method: HTTP method, e.g. ``"GET"``.
            path: Path relative to ``base_url``, e.g. ``"/anime/releases/latest"``.
            params: Query parameters, passed to ``httpx`` as is.
            json: JSON request body.
            with_token: Whether to send ``token``. ``False`` for the endpoints that refuse a
                logged-in caller (``POST /accounts/otp/login`` answers 403 to one).
            cache: Whether the response may be read from and saved to the cache (see
                above). The SDK's own methods pass it for endpoints whose data doesn't
                change from call to call.
            refresh: Skip reading the cache and fetch from the API; the fresh response
                still replaces the cached one.

        Returns:
            The decoded JSON body (``dict``, ``list``, ...), or ``None`` for an empty body.

        Raises:
            APIError: The API answered with an error status — one of its subclasses for
                404, 422, 429, 401/403, 5xx and HTML pages. 429 and 5xx are raised only once
                retries are exhausted.
            TransportError: The request failed without a response (network error, timeout),
                after retries for idempotent methods.
            ResponseParseError: A successful response wasn't valid JSON.
            RuntimeError: The client has been closed.

        Example:
            ```python
            roles = await client.http.request("GET", "/teams/roles", cache=True)
            ```
        """
        store = self._cache
        cacheable = (
            cache
            and store is not None
            and method.upper() == "GET"
            and json is None
            and not (with_token and self._token is not None)
        )
        if not cacheable or store is None:
            response = await self._send_with_retries(
                method, path, params=params, json=json, with_token=with_token
            )
            return _handle_response(response)

        query = sorted(httpx.QueryParams(params).multi_items()) if params else []
        key = jsonlib.dumps(["GET", self.url(path), query], ensure_ascii=False)
        if not refresh:
            cached = store.get(key)
            if cached is not None:
                logger.debug("GET %s: from cache", httpx.URL(self.url(path), params=params))
                return cached
        response = await self._send_with_retries(
            method, path, params=params, json=None, with_token=with_token
        )
        data = _handle_response(response)
        if data is not None:
            try:
                store.set(key, data)
            except OSError as exc:  # the data is in hand; a cache must not fail the request
                logger.warning(
                    "Couldn't write to the response cache in %s: %s", store.directory, exc
                )
        return data

    async def request_raw(
        self, method: str, path: str, *, params: Mapping[str, Any] | None = None
    ) -> httpx.Response:
        """Send a request for a non-JSON resource (a file, an XML feed) and return the response.

        Same limits, retries and error handling as ``request()``; the body is fully read, so
        use ``stream()`` instead for large downloads.

        Args:
            method: HTTP method, e.g. ``"GET"``.
            path: Path relative to ``base_url``.
            params: Query parameters, passed to ``httpx`` as is.

        Returns:
            The successful ``httpx.Response``, with ``content``/``text`` and headers.

        Raises:
            APIError: The API answered with an error status — see ``request()``.
            TransportError: The request failed without a response.
            RuntimeError: The client has been closed.

        Example:
            ```python
            response = await client.http.request_raw("GET", "/anime/torrents/rss")
            print(response.headers["Content-Type"], len(response.text))
            ```
        """
        response = await self._send_with_retries(method, path, params=params, json=None)
        _raise_if_failed(response)
        return response

    @contextlib.asynccontextmanager
    async def stream(
        self, method: str, path: str, *, params: Mapping[str, Any] | None = None
    ) -> AsyncIterator[httpx.Response]:
        """Send a request and stream the response body, for downloads.

        Limits and retries apply until the response headers arrive: a 429/5xx is retried
        before anything is yielded, and an error status raises like ``request()``. The body is
        then read by the caller (``response.aiter_bytes()``); the response is closed when the
        ``async with`` block exits.

        Args:
            method: HTTP method, e.g. ``"GET"``.
            path: Path relative to ``base_url``.
            params: Query parameters, passed to ``httpx`` as is.

        Yields:
            The successful ``httpx.Response``, body not read yet.

        Raises:
            APIError: The API answered with an error status — see ``request()``.
            TransportError: The request failed without a response.
            RuntimeError: The client has been closed.

        Example:
            ```python
            async with client.http.stream("GET", "/anime/torrents/40407/file") as response:
                async for chunk in response.aiter_bytes():
                    ...
            ```
        """
        response = await self._send_with_retries(
            method, path, params=params, json=None, stream=True
        )
        try:
            if not response.is_success or _media_type(response) == "text/html":
                await response.aread()
                _raise_if_failed(response)
            yield response
        finally:
            await response.aclose()

    async def _send_with_retries(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None,
        json: Any,
        stream: bool = False,
        with_token: bool = True,
    ) -> httpx.Response:
        """Send a request, retrying as described on the class; return the final response.

        With ``stream=True`` the returned response's body is not read yet, and responses
        that are retried are closed before the next attempt.
        """
        if self._closed:
            raise RuntimeError("This client has been closed; create a new AniLiberty instance.")
        method = method.upper()
        url = self.url(path)
        attempt = 0
        while True:
            try:
                response = await self._send(
                    method, url, params=params, json=json, stream=stream, with_token=with_token
                )
            except httpx.TransportError as exc:
                logger.debug("%s %s failed: %r", method, url, exc)
                if method in IDEMPOTENT_METHODS and attempt < self._max_retries:
                    await self._wait_before_retry(
                        self._backoff(attempt), attempt, method, url, type(exc).__name__
                    )
                    attempt += 1
                    continue
                raise TransportError(
                    f"Request failed: {type(exc).__name__}: {exc}", method=method, url=url
                ) from exc
            logger.debug("%s %s -> %d", method, response.request.url, response.status_code)
            delay = self._retry_delay(response, method, attempt)
            if delay is None:
                return response
            if stream:
                await response.aclose()
            await self._wait_before_retry(
                delay, attempt, method, url, f"HTTP {response.status_code}"
            )
            attempt += 1

    async def _send(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None,
        json: Any,
        stream: bool = False,
        with_token: bool = True,
    ) -> httpx.Response:
        """Send one attempt, within the concurrency limit and after the pacing delay.

        The concurrency slot is held until the response headers arrive; a streamed body is
        read afterwards, outside of it.
        """
        async with self._semaphore:
            await self._pace()
            headers = self._headers
            if with_token and self._token is not None:
                headers = headers.copy()
                headers["Authorization"] = f"Bearer {self._token}"
            request = self._client.build_request(
                method, url, params=params, json=json, headers=headers
            )
            return await self._client.send(request, stream=stream)

    async def _pace(self) -> None:
        """Wait, if needed, so this request starts at least ``request_delay`` after the last."""
        if self._request_delay <= 0:
            return
        async with self._pacing_lock:
            if self._last_request_at is not None:
                wait = self._last_request_at + self._request_delay - self._clock()
                if wait > 0:
                    await self._sleep(wait)
            self._last_request_at = self._clock()

    def _retry_delay(self, response: httpx.Response, method: str, attempt: int) -> float | None:
        """How long to wait before retrying ``response``, or ``None`` to not retry it."""
        if attempt >= self._max_retries:
            return None
        if response.status_code == 429:
            retry_after = _retry_after(response)
            if retry_after is None:
                return self._backoff(attempt)
            return retry_after if retry_after <= self._max_retry_after else None
        if response.is_server_error and method in IDEMPOTENT_METHODS:
            return self._backoff(attempt)
        return None

    def _backoff(self, attempt: int) -> float:
        delay: float = self._retry_base_delay * 2**attempt
        return delay

    async def _wait_before_retry(
        self, delay: float, attempt: int, method: str, url: str, reason: str
    ) -> None:
        logger.info(
            "%s %s: %s, retrying in %.1fs (retry %d of %d)",
            method,
            url,
            reason,
            delay,
            attempt + 1,
            self._max_retries,
        )
        await self._sleep(delay)


def _handle_response(response: httpx.Response) -> Any:
    """Return the decoded JSON body of a successful response, or raise the matching error."""
    _raise_if_failed(response)
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError as exc:  # json.JSONDecodeError and UnicodeDecodeError
        raise ResponseParseError(
            "Response body is not valid JSON", url=str(response.request.url), payload=response.text
        ) from exc


def _raise_if_failed(response: httpx.Response) -> None:
    """Raise the matching error for an HTML page or an error status; do nothing otherwise."""
    method = response.request.method
    url = str(response.request.url)
    # Some endpoints answer with an empty text/html body (a 200 for success with nothing to
    # return, a 404 for an unknown social-login state); only an actual page is a block.
    is_html_page = _media_type(response) == "text/html" and bool(response.content.strip())
    if is_html_page and not response.is_server_error:
        raise AccessBlockedError(
            "Got an HTML page instead of JSON: the request was likely stopped by the "
            "anti-bot protection in front of the API. Retrying won't help; if the API opens "
            "in a browser on this network, try a mirror via base_url=...",
            status_code=response.status_code,
            method=method,
            url=url,
            payload=response.text,
        )
    if not response.is_success:
        _raise_for_error(response, method=method, url=url)


def _raise_for_error(response: httpx.Response, *, method: str, url: str) -> NoReturn:
    payload = _decode_error_body(response)
    status = response.status_code
    message = _error_message(payload) or response.reason_phrase
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


def _error_message(payload: Any) -> str | None:
    """Pick the human-readable message out of an error body.

    Most errors carry Laravel's ``{"message": ...}``; a failed login answers 401 with
    ``{"token": null, "error": ...}`` instead.
    """
    if not isinstance(payload, dict):
        return None
    for key in ("message", "error"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


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
    """Parse ``Retry-After`` — delay seconds or an HTTP date — into seconds from now.

    An HTTP date is measured against the response's own ``Date`` header when present, so a
    skewed local clock doesn't distort it.
    """
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    retry_at = _parse_http_date(value)
    if retry_at is None:
        return None
    now = _parse_http_date(response.headers.get("Date", "")) or datetime.now(UTC)
    return max(0.0, (retry_at - now).total_seconds())


def _parse_http_date(value: str) -> datetime | None:
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_HEADERS",
    "DEFAULT_MAX_CONCURRENCY",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_MAX_RETRY_AFTER",
    "DEFAULT_REQUEST_DELAY",
    "DEFAULT_RETRY_BASE_DELAY",
    "DEFAULT_SITE_URL",
    "DEFAULT_TIMEOUT",
    "IDEMPOTENT_METHODS",
    "HttpClient",
]
