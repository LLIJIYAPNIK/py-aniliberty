"""Response cache: answer repeated requests from disk instead of the API.

AniLiberty(cache_dir=..., cache_ttl=...) keeps the raw JSON of successful responses in a
directory, one file per request, and serves identical calls from there until the TTL runs
out. It pays off for data that changes rarely but is asked for often — a franchise shown on
every page of a website, the catalog's reference lists, repeated searches.

Which calls are cached is decided per method: exactly the ones with a `refresh` parameter.
Random picks, episodes (their HLS links), torrents and account data always go to the API.
"""

import asyncio
import logging
import tempfile
import time
from pathlib import Path
from urllib.parse import unquote

from aniliberty import AniLiberty


class RequestLog(logging.Handler):
    """Prints how each request was answered, from the SDK's own debug log."""

    def emit(self, record: logging.LogRecord) -> None:
        message = unquote(record.getMessage()).replace("https://aniliberty.top/api/v1", "")
        if message.endswith(": from cache"):
            print("   [cache]", message.removesuffix(": from cache"))
        elif " -> " in message:
            print("   [api]  ", message.rsplit(" -> ", 1)[0])


async def main() -> None:
    logger = logging.getLogger("aniliberty")
    logger.setLevel(logging.DEBUG)  # "GET <url> -> 200" for the network, ": from cache" for hits
    logger.addHandler(RequestLog())

    # A temporary directory keeps this script's output the same on every run. In real use
    # pick a fixed one, e.g. cache_dir=".aniliberty_cache": the cache then survives restarts
    # and is shared by every process pointed at it.
    with tempfile.TemporaryDirectory() as cache_dir:
        # cache_ttl is in seconds; None (the default) means entries never expire on their own.
        async with AniLiberty(cache_dir=cache_dir, cache_ttl=6 * 3600) as client:
            print("1. First call — goes to the API and fills the cache:")
            start = time.perf_counter()
            franchises = await client.franchises.for_release(9839)
            first = time.perf_counter() - start
            print(f"   {[f.name for f in franchises]} in {first * 1000:.0f} ms")

            print("2. Same call again — answered from disk:")
            start = time.perf_counter()
            again = await client.franchises.for_release(9839)
            second = time.perf_counter() - start
            # What's cached is the raw JSON, not the model: every hit is validated anew, so
            # you get equal (not identical) objects, and the cache keeps working across SDK
            # upgrades that change models.
            print(f"   equal: {again == franchises}, in {second * 1000:.0f} ms")

            print("3. refresh=True — skips the cache, and the fresh response replaces it:")
            await client.franchises.for_release(9839, refresh=True)

            print("4. Different arguments are a different entry (key = URL + sorted query):")
            await client.app.search_releases("frieren")
            await client.app.search_releases("frieren")
            await client.app.search_releases("Фрирен")

            print("5. Iterators cache every page they fetch (here two pages, twice):")
            for _ in range(2):
                titles = [
                    r.name.main
                    async for r in client.catalog.iter_releases(search="frieren", limit=1)
                ]
            print(f"   {len(titles)} releases")

            print("6. Methods without `refresh` never use the cache — random picks, for one:")
            await client.releases.random(limit=1)
            await client.releases.random(limit=1)

            # Nothing user-specific may land on disk: while a session token is set, every
            # request bypasses the cache, even for public data (torrent magnets carry the
            # account's passkey, HLS links say isAuthorized=1). Public endpoints accept any
            # token, so a dummy one shows the effect without logging in.
            print("7. With a session token, the cache is not used at all:")
            client.token = "not-a-real-session-token"
            await client.franchises.for_release(9839)
            client.token = None

        print("8. A new client on the same directory reuses what the first one cached:")
        async with AniLiberty(cache_dir=cache_dir) as client:
            await client.franchises.for_release(9839)
            print(f"   {len(list(Path(cache_dir).iterdir()))} files in the cache directory")


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-17):
#
# 1. First call — goes to the API and fills the cache:
#    [api]   GET /anime/franchises/release/9839
#    ['Поднятие уровня в одиночку'] in 473 ms
# 2. Same call again — answered from disk:
#    [cache] GET /anime/franchises/release/9839
#    equal: True, in 9 ms
# 3. refresh=True — skips the cache, and the fresh response replaces it:
#    [api]   GET /anime/franchises/release/9839
# 4. Different arguments are a different entry (key = URL + sorted query):
#    [api]   GET /app/search/releases?query=frieren
#    [cache] GET /app/search/releases?query=frieren
#    [api]   GET /app/search/releases?query=Фрирен
# 5. Iterators cache every page they fetch (here two pages, twice):
#    [api]   GET /anime/catalog/releases?f[search]=frieren&page=1&limit=1
#    [api]   GET /anime/catalog/releases?f[search]=frieren&page=2&limit=1
#    [cache] GET /anime/catalog/releases?f[search]=frieren&page=1&limit=1
#    [cache] GET /anime/catalog/releases?f[search]=frieren&page=2&limit=1
#    2 releases
# 6. Methods without `refresh` never use the cache — random picks, for one:
#    [api]   GET /anime/releases/random?limit=1
#    [api]   GET /anime/releases/random?limit=1
# 7. With a session token, the cache is not used at all:
#    [api]   GET /anime/franchises/release/9839
# 8. A new client on the same directory reuses what the first one cached:
#    [cache] GET /anime/franchises/release/9839
#    5 files in the cache directory
