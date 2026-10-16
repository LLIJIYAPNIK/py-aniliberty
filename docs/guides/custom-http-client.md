# Mirrors and a custom HTTP client

By default the SDK talks to `https://aniliberty.top/api/v1` through an `httpx.AsyncClient` it
creates and closes itself. Both can be changed: `base_url` picks the host, `http_client` hands
the SDK your own `httpx.AsyncClient`.

[`examples/15_custom_http_client_and_mirrors.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/15_custom_http_client_and_mirrors.py)
is a runnable version of this page.

## Mirrors

The API is served on two hosts, with the same data and the same responses:

| Host | `base_url` |
|---|---|
| main server (the default) | `https://aniliberty.top/api/v1` |
| mirror | `https://anilibria.top/api/v1` |

```python
async with AniLiberty(base_url="https://anilibria.top/api/v1") as client:
    release = await client.releases.get("sousou-no-frieren")
    release.poster.preview_url
    # 'https://anilibria.top/storage/releases/posters/9542/....jpg'
```

`base_url` includes the `/api/v1` prefix. Image paths in responses are relative, and the SDK
resolves them against the host of `base_url`, so image URLs point at the host you use.

### Failing over

Try hosts in order and keep the first one that answers. Catch the errors another host can fix
— no response, a block page, server errors — and keep the health check's timeout short: a dead
host costs the SDK's retries first, about `4 × timeout + 7 s`.

```python
from aniliberty import AccessBlockedError, AniLiberty, ServerError, TransportError

HOSTS = ["https://aniliberty.top/api/v1", "https://anilibria.top/api/v1"]


async def first_working(base_urls: list[str], *, timeout: float = 2.0) -> str:
    for base_url in base_urls:
        try:
            async with AniLiberty(base_url=base_url, timeout=timeout) as client:
                if (await client.app.status()).is_alive:
                    return base_url
        except (TransportError, AccessBlockedError, ServerError):
            continue
    raise RuntimeError("No API host is reachable")


async with AniLiberty(base_url=await first_working(HOSTS)) as client:
    ...
```

With one unreachable host ahead of the main one, this took 14 s in the example run.

## Your own `httpx.AsyncClient`

Pass `http_client=` for anything `httpx` can do — a proxy, detailed timeouts, connection
limits, event hooks, a custom transport:

```python
import httpx

http_client = httpx.AsyncClient(
    proxy="http://user:pass@proxy.example:8080",
    timeout=httpx.Timeout(10.0, connect=5.0),
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
)
async with http_client:
    async with AniLiberty(http_client=http_client) as client:
        ...
```

What comes from where:

| | With `http_client=` |
|---|---|
| Timeout | your client's; `AniLiberty(timeout=...)` is ignored |
| Proxy, TLS, connection pool, transport | your client's |
| Concurrency limit, pacing, retries | the SDK's, on top of your client |
| Headers | your client's, plus the SDK's `Accept`, `User-Agent` and `headers=` on every request |
| Error mapping | the SDK's |
| `base_url` set on the httpx client | ignored — the SDK sends absolute URLs built from its own `base_url` |
| Closing | **yours** — `AniLiberty` doesn't close a client it didn't create |

One `httpx.AsyncClient` can serve several `AniLiberty` instances, e.g. the main host and the
mirror sharing one connection pool:

```python
async with httpx.AsyncClient() as http_client:
    main = AniLiberty(http_client=http_client)
    mirror = AniLiberty(http_client=http_client, base_url="https://anilibria.top/api/v1")
    async with main, mirror:
        ...
```

Each `AniLiberty` still has its own concurrency limit and pacing.

### Event hooks

`httpx` event hooks see every attempt the SDK makes, retries included — handy for metrics or
debugging:

```python
async def log_request(request: httpx.Request) -> None:
    print("->", request.method, request.url)


async def log_response(response: httpx.Response) -> None:
    print("<-", response.status_code, response.request.url)


http_client = httpx.AsyncClient(event_hooks={"request": [log_request], "response": [log_response]})
```

A `response` hook runs as soon as the headers arrive, before the SDK reads the body and maps
the status to an exception. Don't call `response.raise_for_status()` in it: let the SDK raise
its own exceptions.

### Transport-level retries

`httpx.AsyncHTTPTransport(retries=...)` retries failed *connection attempts* inside httpx,
before the SDK sees an error. That adds to the SDK's own retries instead of replacing them, so
it's rarely needed.

## Headers

`headers=` adds headers to every request over the SDK's defaults; a key you pass replaces the
default one, matched case-insensitively. The usual reason is to identify your application:

```python
AniLiberty(headers={"User-Agent": "my-app/1.0 (+https://example.com)"})
```

The defaults are `Accept: application/json` and
`User-Agent: py-aniliberty/<version> (+https://github.com/LLIJIYAPNIK/py-aniliberty)`.

!!! warning "Keep `Accept: application/json`"
    Without it the API renders errors as HTML pages, which the SDK reports as
    [`AccessBlockedError`][aniliberty.AccessBlockedError] instead of `NotFoundError` and the
    rest. Override `Accept` only if you know why.
