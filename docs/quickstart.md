# Quickstart

## The client

All requests go through one [`AniLiberty`][aniliberty.AniLiberty] instance. Use it as an async
context manager so its connection pool is closed at the end:

```python
from aniliberty import AniLiberty

async with AniLiberty() as client:
    ...
```

Without `async with`, call `await client.aclose()` when you're done. A closed client can't be
reused — create a new one.

The API is grouped into namespaces that follow the tags of its OpenAPI spec:

| Namespace | What's in it |
|---|---|
| `client.app` | API status, quick search |
| `client.releases` | latest, random and recommended releases; a release by ID or alias; its team members; several releases at once |
| `client.episodes` | an episode with its HLS playlists |
| `client.catalog` | the release catalog with filters, sorting and pagination — see [Catalog filters](guides/catalog-filters.md) |
| `client.genres` | genres with images and counts, random genres, the releases of a genre |
| `client.franchises` | franchises — related releases in watch order, and the franchise of a release |
| `client.schedule` | the airing schedule — yesterday/today/tomorrow and the whole week |
| `client.catalog.references` | the values catalog filters accept: genres, types, seasons, years, age ratings, statuses, sorting |
| `client.http` | the low-level client — `client.http.request(...)` returns raw JSON for endpoints not covered yet |

## A tour

```python
import asyncio

from aniliberty import AniLiberty, NotFoundError


async def main() -> None:
    async with AniLiberty() as client:
        status = await client.app.status()
        print("API alive:", status.is_alive)

        # The latest releases, each with its newest episode.
        for release in await client.releases.latest(limit=3):
            episode = release.latest_episode
            number = episode.ordinal if episode else "-"
            print(f"{release.name.main} — episode {number}")

        # Quick search by Russian or English name, or alias.
        found = await client.app.search_releases("frieren")
        print("Found:", [r.name.main for r in found])

        # A single release by ID or alias, with all its episodes.
        release = await client.releases.get("sousou-no-frieren")
        print(release.name.english, release.year, release.type.description if release.type else "")
        print("Poster:", release.poster.preview_url if release.poster else None)

        # An episode's HLS playlists. Not every episode has 1080p.
        episode = await client.episodes.get(release.episodes[0].id)
        print("Playlist:", (episode.hls_1080 or episode.hls_720 or "")[:60], "...")

        try:
            await client.releases.get("no-such-release")
        except NotFoundError as error:
            print("Not found:", error.status_code)


asyncio.run(main())
```

Output of a real run (2026-10-16):

```text
API alive: True
О моём перерождении в меч 2 — episode 3
Во всеоружии: Сила артефактов — episode 3
Операция: Семейка Ёдзакура 2. Часть 2 — episode 1
Found: ['Провожающая в последний путь Фрирен', 'Провожающая в последний путь Фрирен 2']
Sousou no Frieren 2023 ТВ
Poster: https://aniliberty.top/storage/releases/posters/9542/PaDTDJMU3ybqwWr5BRXydhSM8qbwIhBd.jpg
Playlist: https://cache.libria.fun/videos/media/ts/9542/1/1080/aa675e5 ...
Not found: 404
```

## Things worth knowing

**Value + description fields.** Enumerations such as a release's type, season or publish day
are [`ValueDescription`][aniliberty.ValueDescription] objects: compare `.value`
(`"TV"`, `"autumn"`, `5`), show `.description` (`"ТВ"`, `"Осень"`, `"Пятница"`). Optional ones
can be `None`.

**Images.** The API sends relative paths; [`Image`][aniliberty.Image] keeps them in
`preview`/`thumbnail`/`src` and gives absolute URLs in `preview_url`/`thumbnail_url`/`src_url`,
on the host the client talks to. `image.optimized` has the same image in WebP.

**HLS links** are returned exactly as the API sends them — the query string is part of the
link. The SDK doesn't download video; hand the playlist to a player or to `ffmpeg`.

**Pagination.** Endpoints with pages return a [`Page`][aniliberty.Page] (`items`, `page`,
`total_pages`, `has_next_page`, ...) and have an `iter_*()` twin that walks all pages for you
(more in the [Pagination](guides/pagination.md) guide):

```python
async for release in client.releases.iter_list(ids=[9542, 10172, 10297], limit=50):
    print(release.name.main)
```

**Limits.** `limit` on the release endpoints is 1 to 50; anything else is rejected by the API
with a [`ValidationError`][aniliberty.ValidationError].

**Errors.** Everything the SDK raises on purpose is an
[`AniLibertyError`][aniliberty.AniLibertyError]. Rate limits (429), server errors (5xx) and
network errors are retried automatically before an exception reaches you.

**Mirrors.** The default host is `https://aniliberty.top/api/v1`; `https://anilibria.top/api/v1`
serves the same API:

```python
async with AniLiberty(base_url="https://anilibria.top/api/v1") as client:
    ...
```

**Concurrency.** `asyncio.gather` over many calls is fine: the client itself keeps at most
`max_concurrency` (default 5) requests in flight.

```python
releases = await asyncio.gather(*(client.releases.get(i) for i in (9542, 10172, 10297)))
```

**Logging.** The SDK logs to the `aniliberty` logger: every request at `DEBUG`, retries at
`INFO`.
