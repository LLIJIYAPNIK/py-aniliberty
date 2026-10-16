"""Exceptions raised by the SDK.

Hierarchy::

    AniLibertyError
    ├── APIError                 the API (or the edge in front of it) answered with an error
    │   ├── NotFoundError        404
    │   ├── ValidationError      422
    │   ├── RateLimitError       429
    │   ├── AuthRequiredError    401 / 403 with a JSON body
    │   ├── ServerError          5xx
    │   └── AccessBlockedError   an HTML page instead of JSON (WAF / anti-bot)
    ├── TransportError           network error or timeout, no response at all
    └── ResponseParseError       a successful response that doesn't match the expected shape

Catch ``AniLibertyError`` to handle everything the SDK raises on purpose.
"""

from __future__ import annotations

from typing import Any


class AniLibertyError(Exception):
    """Base class for all errors raised by the SDK."""


class APIError(AniLibertyError):
    """The API responded with an error status.

    Raised as is for statuses without a dedicated subclass (e.g. 400, 405, 409); otherwise one
    of the subclasses below is raised, so ``except APIError`` catches all of them.

    Attributes:
        status_code: HTTP status code of the response.
        message: Error message — the ``message`` field of the API's JSON body when it has one,
            otherwise the HTTP reason phrase.
        method: HTTP method of the failed request.
        url: Full URL of the failed request.
        payload: The decoded JSON body of the response, or its text if it wasn't JSON.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        method: str,
        url: str,
        payload: Any = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.method = method
        self.url = url
        self.payload = payload
        super().__init__(f"HTTP {status_code}: {message} ({method} {url})")


class NotFoundError(APIError):
    """The requested resource doesn't exist (404).

    The API's own message for this status is an internal Laravel lookup string such as
    ``"No query results for model [...]"`` — it's kept in ``payload``, while ``message`` is a
    plain ``"Not found"``.
    """


class ValidationError(APIError):
    """The API rejected the request parameters (422).

    Not to be confused with ``pydantic.ValidationError``: this one means the *request* was
    invalid, e.g. ``limit`` above the endpoint's maximum. A response that doesn't fit the SDK's
    models raises ``ResponseParseError`` instead.

    Attributes:
        errors: Messages per parameter, as the API returns them (in Russian), e.g.
            ``{"limit": ["Поле limit не может быть больше 50."]}``.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        method: str,
        url: str,
        payload: Any = None,
        errors: dict[str, list[str]] | None = None,
    ) -> None:
        self.errors: dict[str, list[str]] = errors or {}
        super().__init__(message, status_code=status_code, method=method, url=url, payload=payload)


class RateLimitError(APIError):
    """The API answered 429 Too Many Requests.

    Attributes:
        retry_after: The response's ``Retry-After`` value, in seconds, if it sent one.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        method: str,
        url: str,
        payload: Any = None,
        retry_after: float | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, status_code=status_code, method=method, url=url, payload=payload)


class AuthRequiredError(APIError):
    """The request needs a valid session, or the credentials were wrong (401/403 JSON).

    The API answers 403 ``"This action is unauthorized."`` to an account endpoint called
    without a session token, with a malformed one, or with one that was logged out or has
    expired — it doesn't say which. Log in again (``client.auth.login()``) or pass a fresh
    ``token`` to ``AniLiberty``. Wrong credentials at ``client.auth.login()`` are a 401; the
    API's reason is in ``message``.
    """


class ServerError(APIError):
    """The API (or the CDN in front of it) failed with a 5xx status."""


class AccessBlockedError(APIError):
    """Something in front of the API answered with an HTML page instead of JSON.

    The SDK always sends ``Accept: application/json``, and with that header the API itself
    answers with JSON even for errors (see ``docs/api-notes.md``). An HTML page therefore
    comes from the Cloudflare edge in front of the API — a bot challenge or a block of the
    network/IP. Resending the same request gets the same answer, so this is not retried.

    HTML on a 5xx status is not this error but ``ServerError``: Cloudflare renders its own
    origin errors (502, 520, ...) as HTML pages too, and those are worth retrying.
    """


class TransportError(AniLibertyError):
    """The request failed before any response arrived (connection error, timeout, ...).

    The underlying ``httpx`` exception is available as ``__cause__``.

    Attributes:
        method: HTTP method of the failed request.
        url: Full URL of the failed request.
    """

    def __init__(self, message: str, *, method: str, url: str) -> None:
        self.method = method
        self.url = url
        super().__init__(f"{message} ({method} {url})")


class ResponseParseError(AniLibertyError):
    """A successful response couldn't be decoded or didn't match the SDK's model.

    Usually means the API changed its response format. The raw data is kept so it isn't
    lost: ``payload`` holds the decoded JSON (or the body text if it wasn't JSON), and the
    original ``json``/``pydantic`` exception is available as ``__cause__``.

    Attributes:
        url: Full URL of the request.
        payload: Decoded JSON body, or the body text if it wasn't valid JSON.
    """

    def __init__(self, message: str, *, url: str, payload: Any = None) -> None:
        self.url = url
        self.payload = payload
        super().__init__(f"{message} ({url})")
