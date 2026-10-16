# py-aniliberty

Async Python SDK for the public [AniLibria](https://aniliberty.top) API (v1): releases,
episodes with HLS links, quick search, the catalog with filters, the airing schedule, genres,
franchises, torrents (with `.torrent` downloads and RSS), teams and media — and, with an
account, favorites, collections, watch progress and ratings
([Authentication](guides/authentication.md)). Every endpoint of the API is covered except
the ad ones.

- **Async only**, built on [`httpx`](https://www.python-httpx.org/); every response is a typed,
  immutable [pydantic](https://docs.pydantic.dev/) model.
- **Polite by default**: at most 5 requests in flight, requests spaced 0.1 s apart, and
  automatic retries with backoff on 429, 5xx and network errors (see
  [`HttpClient`][aniliberty.HttpClient]).
- **Clear errors**: one exception per failure kind — `NotFoundError`, `ValidationError`,
  `RateLimitError`, `AccessBlockedError`, ... — all under `AniLibertyError`.
- **Built from the official OpenAPI spec**, checked against the live API; what the spec gets
  wrong is written down in [API notes](api-notes.md).

## Installation

```bash
uv add py-aniliberty
```

or

```bash
pip install py-aniliberty
```

Requires Python 3.11+.

## A first request

```python
import asyncio

from aniliberty import AniLiberty


async def main() -> None:
    async with AniLiberty() as client:
        for release in await client.releases.latest(limit=3):
            print(release.name.main)


asyncio.run(main())
```

Continue with the [Quickstart](quickstart.md), or browse the [API reference](reference.md).
[Endpoints](endpoints.md) maps every operation of the API to its SDK method.

!!! note "Status"
    Pre-1.0: the public API may still change between minor versions; breaking changes are
    called out in the changelog.
