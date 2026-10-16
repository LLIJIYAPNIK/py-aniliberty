"""Mirrors and your own httpx.AsyncClient: where requests go and how they're sent.

base_url picks the host. The API runs on https://aniliberty.top (the default) and on the
mirror https://anilibria.top — same data, same responses. http_client lets you hand the SDK
a ready httpx.AsyncClient for anything httpx can do: proxies, timeouts, connection limits,
event hooks, a custom transport. The SDK keeps its own concurrency limit, pacing, retries,
headers and error mapping on top of whatever client you pass.
"""

import asyncio
import time

import httpx

from aniliberty import AccessBlockedError, AniLiberty, ServerError, TransportError

MAIN = "https://aniliberty.top/api/v1"
MIRROR = "https://anilibria.top/api/v1"


async def first_working(base_urls: list[str], *, timeout: float = 2.0) -> str:
    """Return the first base URL whose API answers, trying them in order.

    Worth catching here: no response at all, a block page (AccessBlockedError is never
    retried, but a mirror may not be blocked), and server errors. Each failing host costs
    the SDK's retries first — 4 attempts with 1 + 2 + 4 s of backoff between them — so keep
    the timeout of this health check short; a dead host then takes about 4 * timeout + 7 s.
    """
    for base_url in base_urls:
        try:
            async with AniLiberty(base_url=base_url, timeout=timeout) as client:
                if (await client.app.status()).is_alive:
                    return base_url
        except (TransportError, AccessBlockedError, ServerError) as error:
            print(f"  {base_url}: {type(error).__name__}")
    raise RuntimeError("No API host is reachable")


async def main() -> None:
    # 1. A mirror is just another base_url. Relative paths in responses (images) resolve
    #    against the host the client talks to, so poster URLs point at the mirror too.
    async with AniLiberty(base_url=MIRROR) as client:
        status = await client.app.status()
        release = await client.releases.get("sousou-no-frieren")
        print("Mirror alive:", status.is_alive, "| hosts it lists:", status.available_api_endpoints)
        print("Poster via mirror:", release.poster.preview_url if release.poster else None)

    # 2. Failover across hosts. The .invalid TLD never resolves, so the first one fails.
    started = time.perf_counter()
    print("Failover:")
    chosen = await first_working(["https://aniliberty.invalid/api/v1", MAIN, MIRROR])
    print(f"  using {chosen} (after {time.perf_counter() - started:.0f}s)")

    # 3. Your own httpx client. Event hooks see every attempt the SDK makes — including
    #    retries — with the headers it adds: Accept: application/json (needed for JSON error
    #    bodies) and its User-Agent, here replaced through headers=.
    async def log_request(request: httpx.Request) -> None:
        print(f"  -> {request.method} {request.url.path} UA={request.headers['User-Agent']!r}")

    async def log_response(response: httpx.Response) -> None:
        print(f"  <- {response.status_code} {response.headers.get('Content-Type')}")

    http_client = httpx.AsyncClient(
        # With http_client=..., AniLiberty(timeout=...) is ignored — set it here.
        timeout=httpx.Timeout(10.0, connect=5.0),
        # httpx's own pool limit; the SDK's max_concurrency still applies on top.
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        event_hooks={"request": [log_request], "response": [log_response]},
        # proxy="http://user:pass@proxy.example:8080",  # e.g. to reach the API via a proxy
    )
    print("Custom client:")
    async with http_client:
        # One httpx client (one connection pool) can serve several AniLiberty instances —
        # e.g. the main host and the mirror.
        main_client = AniLiberty(http_client=http_client, headers={"User-Agent": "my-app/1.0"})
        mirror_client = AniLiberty(http_client=http_client, base_url=MIRROR)
        async with main_client, mirror_client:
            await main_client.app.status()
            await mirror_client.genres.random(limit=1)
        # Closing AniLiberty doesn't close a client it didn't create — its owner does.
        print("  httpx client closed after AniLiberty exits?", http_client.is_closed)
    print("  ...and after its own async with?", http_client.is_closed)


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# Mirror alive: True | hosts it lists: ['https://aniliberty.top']
# Poster via mirror: https://anilibria.top/storage/releases/posters/9542/PaDTDJMU3ybqwWr5BRXydhSM8qbwIhBd.jpg
# Failover:
#   https://aniliberty.invalid/api/v1: TransportError
#   using https://aniliberty.top/api/v1 (after 14s)
# Custom client:
#   -> GET /api/v1/app/status UA='my-app/1.0'
#   <- 200 application/json
#   -> GET /api/v1/anime/genres/random UA='py-aniliberty/0.2.0 (+https://github.com/LLIJIYAPNIK/py-aniliberty)'
#   <- 200 application/json
#   httpx client closed after AniLiberty exits? False
#   ...and after its own async with? True
