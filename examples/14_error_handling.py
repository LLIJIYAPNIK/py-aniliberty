"""Error handling: what the SDK raises, what's retried for you, and what to do about each.

Every error the SDK raises on purpose is an AniLibertyError:

    AniLibertyError
    ├── APIError                 the API answered with an error status
    │   ├── NotFoundError        404
    │   ├── ValidationError      422 — bad parameters (NOT pydantic's ValidationError)
    │   ├── RateLimitError       429, after retries
    │   ├── AuthRequiredError    401 / 403
    │   ├── ServerError          5xx, after retries
    │   └── AccessBlockedError   an HTML page instead of JSON (anti-bot / WAF)
    ├── TransportError           no response at all (network, timeout), after retries
    └── ResponseParseError       the response didn't fit the SDK's model

Wrong argument types (an alias where only a numeric ID works, ...) are caught before any
request and raise the built-in TypeError/ValueError — those are bugs in the calling code, not
API errors, so they're deliberately outside this hierarchy.
"""

import asyncio
import logging
import time

from aniliberty import (
    AccessBlockedError,
    AniLiberty,
    AniLibertyError,
    APIError,
    NotFoundError,
    RateLimitError,
    ResponseParseError,
    ServerError,
    TransportError,
    ValidationError,
)


def explain(error: AniLibertyError) -> str:
    """A typical except-ladder: most specific classes first, the base class last."""
    if isinstance(error, NotFoundError):
        return "doesn't exist — check the ID/alias"
    if isinstance(error, ValidationError):
        # .errors is {parameter: [messages]}, in Russian, straight from the API.
        return f"bad parameters: {error.errors}"
    if isinstance(error, RateLimitError):
        # Already retried; retry_after (seconds) is set when the API sent Retry-After.
        return f"rate limited, retry after {error.retry_after}s"
    if isinstance(error, AccessBlockedError):
        # Never retried: the same request gets the same block page. Try a mirror.
        return "blocked by the anti-bot protection — try base_url of a mirror"
    if isinstance(error, ServerError):
        return "the API is having problems (already retried) — try again later"
    if isinstance(error, APIError):
        # Any other status, e.g. 405. status_code/message/payload/url are on every APIError.
        return f"HTTP {error.status_code}: {error.message}"
    if isinstance(error, TransportError):
        # The original httpx exception is the cause.
        return f"no response ({type(error.__cause__).__name__}) — network or timeout"
    if isinstance(error, ResponseParseError):
        # The raw data is kept in .payload, so nothing is lost if the API changed its format.
        return "the response didn't match the model — raw JSON is in error.payload"
    return str(error)


async def main() -> None:
    async with AniLiberty() as client:
        # 404: message is a plain "Not found"; the API's own (Laravel) text is in payload.
        try:
            await client.releases.get("no-such-release")
        except NotFoundError as error:
            print("NotFoundError:", error.status_code, error.message, "|", error.payload)
            print("  url:", error.url)

        # 422: the API validates parameters itself — limit is 1 to 50 here.
        try:
            await client.releases.latest(limit=51)
        except ValidationError as error:
            print("ValidationError:", error.errors)

        # Statuses without a dedicated class raise APIError itself. The low-level
        # client.http.request() maps errors exactly like the typed methods.
        try:
            await client.http.request("POST", "/app/status")
        except APIError as error:
            print(f"{type(error).__name__}:", explain(error))

        # Checked before sending anything: TypeError, not an AniLibertyError.
        try:
            await client.franchises.for_release("sousou-no-frieren")  # type: ignore[arg-type]
        except TypeError as error:
            print("TypeError:", str(error).split(";")[0])

        # One except-ladder for everything the API can throw at you.
        for call in (client.releases.get("no-such-release"), client.genres.releases(1, limit=31)):
            try:
                await call
            except AniLibertyError as error:
                print(f"{type(error).__name__}: {explain(error)}")

    # Retries are automatic: 429, 5xx and network errors/timeouts are retried up to 3 times
    # with 1 s, 2 s, 4 s backoff (or the API's Retry-After) before you see an exception. The
    # SDK logs each retry at INFO on the "aniliberty" logger — turn it on to watch them.
    # A 1 ms timeout makes every attempt time out, so this takes about 7 seconds. (Log lines
    # go to stderr; the expected output below interleaves both streams.)
    logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("aniliberty").setLevel(logging.INFO)
    async with AniLiberty(timeout=0.001) as client:
        started = time.perf_counter()
        try:
            await client.app.status()
        except TransportError as error:
            print(f"TransportError after {time.perf_counter() - started:.0f}s:", explain(error))


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# NotFoundError: 404 Not found | {'message': 'No query results for model [App\\Modules\\Anime\\Releases\\Models\\Release\\Release].'}
#   url: https://aniliberty.top/api/v1/anime/releases/no-such-release
# ValidationError: {'limit': ['Поле limit не может быть больше 50.']}
# APIError: HTTP 405: The POST method is not supported for route api/v1/app/status. Supported methods: GET, HEAD.
# TypeError: Expected a release ID (int) or a Release, got 'sousou-no-frieren'
# NotFoundError: doesn't exist — check the ID/alias
# ValidationError: bad parameters: {'limit': ['Поле limit не может быть больше 30.']}
# INFO aniliberty: GET https://aniliberty.top/api/v1/app/status: ConnectTimeout, retrying in 1.0s (retry 1 of 3)
# INFO aniliberty: GET https://aniliberty.top/api/v1/app/status: ConnectTimeout, retrying in 2.0s (retry 2 of 3)
# INFO aniliberty: GET https://aniliberty.top/api/v1/app/status: ConnectTimeout, retrying in 4.0s (retry 3 of 3)
# TransportError after 7s: no response (ConnectTimeout) — network or timeout
