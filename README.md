# py-aniliberty

Async Python SDK for the public [AniLibria](https://anilibria.top) API (v1): releases,
episodes (HLS links), catalog with filters, schedule, franchises, genres, and torrents.

> **Status:** early development. Releases, episodes (HLS links) and quick search are
> implemented; the catalog, schedule, genres, franchises and torrents are next — see
> [`ROADMAP.md`](ROADMAP.md).

**Documentation:** <https://llijiyapnik.github.io/py-aniliberty/>

## Installation

Not published yet. Once released:

```bash
uv add py-aniliberty
```

or

```bash
pip install py-aniliberty
```

Requires Python 3.11+.

## Quickstart

```python
import asyncio

from aniliberty import AniLiberty


async def main() -> None:
    async with AniLiberty() as client:
        for release in await client.releases.latest(limit=3):
            print(release.name.main)

        release = await client.releases.get("sousou-no-frieren")
        episode = await client.episodes.get(release.episodes[0].id)
        print(episode.hls_1080 or episode.hls_720)


asyncio.run(main())
```

More in the [Quickstart](https://llijiyapnik.github.io/py-aniliberty/quickstart/) of the docs.

## License

[MIT](LICENSE)
