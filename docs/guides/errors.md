# Errors and retries

Everything the SDK raises on purpose is an [`AniLibertyError`][aniliberty.AniLibertyError].
Failures that are likely to go away — rate limits, server errors, network problems — are
retried automatically before an exception reaches you.

[`examples/14_error_handling.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/14_error_handling.py)
is a runnable version of this page.

## The exception hierarchy

```text
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
```

| Exception | When | Retried | What to do |
|---|---|---|---|
| [`NotFoundError`][aniliberty.NotFoundError] | unknown ID or alias, unknown path | no | check the identifier |
| [`ValidationError`][aniliberty.ValidationError] | the API rejected a parameter, e.g. `limit` too big | no | fix the call; `error.errors` names the parameter |
| [`RateLimitError`][aniliberty.RateLimitError] | 429 | yes | slow down; `error.retry_after` if the API sent it |
| [`ServerError`][aniliberty.ServerError] | 5xx | yes | try again later |
| [`AccessBlockedError`][aniliberty.AccessBlockedError] | an HTML page instead of JSON | **never** | try the [mirror](custom-http-client.md#mirrors) or another network |
| [`AuthRequiredError`][aniliberty.AuthRequiredError] | 401 wrong credentials, 403 no valid session | no | log in again — see [Authentication](authentication.md#when-a-session-is-missing-or-invalid) |
| [`APIError`][aniliberty.APIError] | any other error status, e.g. 405 | no | — |
| [`TransportError`][aniliberty.TransportError] | connection error, timeout | yes | check the network; `error.__cause__` is the `httpx` exception |
| [`ResponseParseError`][aniliberty.ResponseParseError] | the response didn't fit the SDK's model | no | [report it](#responseparseerror); the raw data is in `error.payload` |

Every `APIError` carries `status_code`, `message`, `method`, `url` and `payload` (the decoded
JSON body, or its text). Values from the live API:

```python
try:
    await client.releases.get("no-such-release")
except NotFoundError as error:
    error.status_code  # 404
    error.message  # 'Not found'
    error.payload  # {'message': 'No query results for model [App\\...\\Release].'}

try:
    await client.releases.latest(limit=51)
except ValidationError as error:
    error.errors  # {'limit': ['Поле limit не может быть больше 50.']}
```

!!! note "Two `ValidationError`s"
    `aniliberty.ValidationError` means the *request* was invalid (HTTP 422). It is not
    `pydantic.ValidationError` — a response that doesn't fit the models raises
    `ResponseParseError` instead, so you never need to catch pydantic's exception.

## Argument errors are not API errors

Arguments the SDK can check itself are checked before anything is sent, and raise the built-in
`TypeError` or `ValueError` — for example an alias where the API only accepts a numeric ID
(`client.franchises.for_release("sousou-no-frieren")`), or an ID containing `/`. These are bugs
in the calling code, so they are deliberately not `AniLibertyError`s.

## Catching

Most specific first, the base class last:

```python
try:
    release = await client.releases.get(alias)
except NotFoundError:
    release = None
except (TransportError, ServerError, RateLimitError):
    raise  # already retried: the API or the network is in trouble
except AniLibertyError:
    log.exception("AniLibria API call failed")
    raise
```

## Retries

Every SDK method sends `GET` requests, which are retried on 429, 5xx and network
errors/timeouts:

- up to **3 retries** (4 attempts in total);
- the delay is the response's `Retry-After` (seconds or an HTTP date) when it has one,
  otherwise **1 s, 2 s, 4 s**;
- a `Retry-After` longer than **60 s** isn't waited out: `RateLimitError` is raised at once
  with that value in `retry_after`;
- 404, 422, other 4xx and HTML block pages are never retried — the same request would get the
  same answer.

For requests that aren't idempotent (`POST`, `PATCH` through `client.http.request()`) only 429
is retried: after a 5xx or a dropped connection it's unknown whether the server already acted.

The exception you get is the one from the last attempt, so a `ServerError` or
`TransportError` means the problem lasted through about 7 seconds of backoff.

### Seeing retries

The SDK logs to the standard `logging` logger `aniliberty`: every request at `DEBUG`, every
retry at `INFO`.

```python
import logging

logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("aniliberty").setLevel(logging.INFO)
```

```text
INFO aniliberty: GET https://aniliberty.top/api/v1/app/status: ConnectTimeout, retrying in 1.0s (retry 1 of 3)
INFO aniliberty: GET https://aniliberty.top/api/v1/app/status: ConnectTimeout, retrying in 2.0s (retry 2 of 3)
INFO aniliberty: GET https://aniliberty.top/api/v1/app/status: ConnectTimeout, retrying in 4.0s (retry 3 of 3)
```

## Timeouts

`AniLiberty(timeout=30.0)` is the timeout of each attempt, in seconds, with `httpx` semantics
(it applies to connecting, reading, writing and waiting for a pooled connection). With retries,
the worst case for one call is about `4 × timeout + 7 s`. For finer control — a short connect
timeout with a long read timeout — pass your own client with an `httpx.Timeout`; see
[Mirrors and a custom HTTP client](custom-http-client.md#your-own-httpxasyncclient).

For a deadline on a whole operation, wrap it in `asyncio.timeout(...)` — see
[Concurrency](concurrency.md#a-deadline-for-a-batch).

## `AccessBlockedError`

The SDK always sends `Accept: application/json`, and with it the API answers with JSON even for
errors. An HTML page therefore comes from the Cloudflare edge in front of the API — a bot
challenge or a block of your network. Repeating the request gets the same page, so it isn't
retried. If the site opens in a browser on the same network, try the mirror
(`base_url="https://anilibria.top/api/v1"`); the page itself is in `error.payload`.

An HTML page with a **5xx** status is a `ServerError` instead: Cloudflare renders its own
origin errors (502, 520, ...) as HTML, and those are worth retrying.

## `ResponseParseError`

Raised when a successful response isn't JSON or doesn't fit the SDK's model — usually because
the API changed its format. Nothing is lost: `error.payload` holds the decoded JSON (or the
body text) and `error.__cause__` the original `pydantic` or `json` exception. Please
[open an issue](https://github.com/LLIJIYAPNIK/py-aniliberty/issues) with the URL; meanwhile
[`client.http.request()`][aniliberty.HttpClient.request] returns the raw JSON of the same
endpoint.
