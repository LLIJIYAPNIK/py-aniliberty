# py-aniliberty

[![PyPI](https://img.shields.io/pypi/v/py-aniliberty)](https://pypi.org/project/py-aniliberty/)
[![License: MIT](https://img.shields.io/github/license/LLIJIYAPNIK/py-aniliberty)](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/LICENSE)
[![Python versions](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/pyproject.toml)
[![CI](https://github.com/LLIJIYAPNIK/py-aniliberty/actions/workflows/ci.yml/badge.svg)](https://github.com/LLIJIYAPNIK/py-aniliberty/actions/workflows/ci.yml)
[![Coverage Status](https://coveralls.io/repos/github/LLIJIYAPNIK/py-aniliberty/badge.svg?branch=main)](https://coveralls.io/github/LLIJIYAPNIK/py-aniliberty?branch=main)
[![Docs](https://github.com/LLIJIYAPNIK/py-aniliberty/actions/workflows/docs.yml/badge.svg)](https://llijiyapnik.github.io/py-aniliberty/)

Async Python SDK for the public [AniLibria](https://aniliberty.top) API (v1): releases,
episodes (HLS links), catalog with filters, schedule, franchises, genres, and torrents.

> **Status:** early development. Releases, episodes (HLS links) and quick search are
> implemented; the catalog, schedule, genres, franchises and torrents are next — see
> [`ROADMAP.md`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/ROADMAP.md).

**Documentation:** <https://llijiyapnik.github.io/py-aniliberty/>

## Installation

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

## Examples

[`examples/`](https://github.com/LLIJIYAPNIK/py-aniliberty/tree/main/examples/) has a runnable, heavily commented script per feature — releases,
episodes and HLS links, quick search, ... — each ending with the output of a real run. See
[`examples/README.md`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/README.md) for the list.

## Changelog

See [`CHANGELOG.md`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/CHANGELOG.md).

## License

[MIT](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/LICENSE)
