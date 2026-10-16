"""Torrents of a release, downloading the .torrent file, and the RSS feeds.

The SDK downloads the small .torrent file (22 KB and 388 KB in the ones checked) — what it
points to, the video itself, is for a torrent client to fetch. A torrent is identified by its
numeric id or its info hash; every method also accepts a Torrent object.
"""

import asyncio
import tempfile
from pathlib import Path

from aniliberty import AniLiberty


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


async def main() -> None:
    async with AniLiberty() as client:
        # Torrents of one release. Note: this endpoint needs the numeric release ID — the
        # API answers an alias with a 404 — so get the Release first (or pass release.id).
        release = await client.releases.get("sousou-no-frieren")
        torrents = await client.torrents.for_release(release)
        print(f"{release.name.main}: {len(torrents)} torrents")
        for torrent in torrents:
            codec = torrent.codec.label if torrent.codec else "?"
            quality = torrent.quality.value if torrent.quality else "?"
            # `size` is the size of the video files, not of the .torrent file.
            print(f"  [{quality} {codec}] episodes {torrent.description}, ", end="")
            print(f"{human_size(torrent.size)}, {torrent.seeders} seeders")

        # A magnet link needs no file at all — hand it straight to a torrent client.
        best = max(torrents, key=lambda t: t.seeders)
        print("Magnet:", best.magnet[:60] + "...")

        # The .torrent file in memory: bytes plus the file name the API suggests.
        torrent_file = await client.torrents.file(best)
        print(f"File: {torrent_file.filename} ({len(torrent_file.content)} bytes)")

        # Or straight to disk. Given a directory, the suggested name is used; the file is
        # streamed to "<name>.part" and renamed only when complete, so an interrupted
        # download never leaves a broken .torrent behind.
        with tempfile.TemporaryDirectory() as folder:
            saved = await client.torrents.download(best, path=folder)
            print(f"Saved: {Path(saved).name}, {saved.stat().st_size} bytes")

        # The same torrent by its hash, in any letter case.
        same = await client.torrents.get(best.hash.upper())
        print("Found by hash:", same.id == best.id)

        # RSS feeds come back as XML text — meant for torrent clients and feed readers.
        # For the same data as models, use torrents.list() / for_release().
        feed = await client.torrents.rss_for_release(release)
        print(f"RSS for the release: {feed.count('<item>')} items, starts with {feed[:38]!r}")
        # The site-wide feed of the newest torrents; limit is how many items it holds.
        latest_feed = await client.torrents.rss(limit=5)
        print(f"Site-wide RSS: {latest_feed.count('<item>')} items")

        # All torrents of the site as models, most recently updated first: list() gives one
        # page, iter_list() walks the pages for you. There are thousands, so stop early.
        page = await client.torrents.list(limit=5)
        print(f"Torrents on the site: {page.total}, {page.total_pages} pages of 5")
        latest = []
        async for torrent in client.torrents.iter_list(limit=50):
            latest.append(torrent)
            if len(latest) == 3:
                break  # no more pages are requested after this
        print("Latest three come with their release:", all(t.release is not None for t in latest))


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# Провожающая в последний путь Фрирен: 2 torrents
#   [1080p HEVC] episodes 1-28, 7.7 GB, 141 seeders
#   [1080p AVC] episodes 1-28, 41.3 GB, 55 seeders
# Magnet: magnet:?xt=urn:btih:2f8f88eb64310eb6c72a2193a068514428583927...
# File: Sousou no Frieren - AniLiberty.TOP [WEBRip 1080p][HEVC][1-28].torrent (22792 bytes)
# Saved: Sousou no Frieren - AniLiberty.TOP [WEBRip 1080p][HEVC][1-28].torrent, 22792 bytes
# Found by hash: True
# RSS for the release: 2 items, starts with '<?xml version="1.0" encoding="UTF-8"?>'
# Site-wide RSS: 5 items
# Torrents on the site: 3128, 626 pages of 5
# Latest three come with their release: True
