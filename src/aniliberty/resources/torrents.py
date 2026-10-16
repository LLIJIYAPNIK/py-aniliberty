"""``client.torrents`` — the ``Аниме.Торренты`` tag of the spec."""

from __future__ import annotations

import builtins
import os
import re
from collections.abc import AsyncIterator
from email.message import Message
from pathlib import Path

import httpx

from aniliberty.models.release import Release
from aniliberty.models.torrent import Torrent, TorrentFile
from aniliberty.pagination import Page, iterate_pages
from aniliberty.resources._base import BaseResource, path_segment
from aniliberty.resources._filters import numeric_release_id

_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class TorrentsResource(BaseResource):
    """Torrents of releases, their ``.torrent`` files and RSS feeds, as ``client.torrents``.

    A torrent is identified by its numeric ``id`` or its info ``hash``; every method that takes
    a torrent also accepts a ``Torrent`` object.
    """

    ENDPOINTS = (
        ("GET", "/anime/torrents"),
        ("GET", "/anime/torrents/{hashOrId}"),
        ("GET", "/anime/torrents/{hashOrId}/file"),
        ("GET", "/anime/torrents/release/{releaseId}"),
        ("GET", "/anime/torrents/rss"),
        ("GET", "/anime/torrents/rss/release/{releaseId}"),
    )

    async def list(self, *, page: int | None = None, limit: int | None = None) -> Page[Torrent]:
        """Get one page of all torrents.

        Args:
            page: Page number, starting at 1.
            limit: Page size, 1 to 50.

        Returns:
            One page of torrents, each with its ``release``, most recently updated first.

        Raises:
            ValidationError: ``page`` or ``limit`` is out of range.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Torrent``.

        Example:
            ```python
            page = await client.torrents.list(limit=10)
            for torrent in page.items:
                print(torrent.label, torrent.size)
            ```
        """
        return await self._get(
            "/anime/torrents", Page[Torrent], params={"page": page, "limit": limit}
        )

    def iter_list(self, *, limit: int | None = None) -> AsyncIterator[Torrent]:
        """Iterate over all torrents (a few thousand), fetching page by page.

        Args:
            limit: Page size, 1 to 50 — affects how many requests are made, not the result.

        Returns:
            An async iterator over the torrents.

        Raises:
            ValidationError: ``limit`` is out of range — raised once iteration starts.
            APIError: The API answered with another error, while iterating.
            TransportError: A request failed without a response, while iterating.

        Example:
            ```python
            async for torrent in client.torrents.iter_list(limit=50):
                print(torrent.hash, torrent.seeders)
            ```
        """

        async def fetch(page: int) -> Page[Torrent]:
            return await self.list(page=page, limit=limit)

        return iterate_pages(fetch)

    async def get(self, torrent: int | str | Torrent) -> Torrent:
        """Get one torrent by its ID or info hash.

        Args:
            torrent: Torrent ID, info hash (any letter case), or a ``Torrent``.

        Returns:
            The torrent, with ``release`` and ``torrent_members``.

        Raises:
            NotFoundError: No torrent with this ID or hash.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Torrent``.

        Example:
            ```python
            torrent = await client.torrents.get("17ceda4b3c2b8823b7f1139dca0b49aea5fff933")
            print(torrent.label, torrent.release.name.main if torrent.release else None)
            ```
        """
        return await self._get(f"/anime/torrents/{_torrent_key(torrent)}", Torrent)

    async def for_release(self, release: int | Release) -> builtins.list[Torrent]:
        """Get the torrents of a release.

        Args:
            release: Release ID, or a ``Release``. Only numeric IDs work here: the API answers
                an alias with a 404 even for an existing release, so a ``str`` is rejected.

        Returns:
            The release's torrents; an empty list if it has none.

        Raises:
            TypeError: ``release`` is not an ``int`` or a ``Release``.
            NotFoundError: No release with this ID.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Torrent``.

        Example:
            ```python
            release = await client.releases.get("sousou-no-frieren")
            for torrent in await client.torrents.for_release(release):
                print(torrent.label, torrent.size, torrent.seeders)
            ```
        """
        return await self._get(
            f"/anime/torrents/release/{numeric_release_id(release)}", builtins.list[Torrent]
        )

    async def file(self, torrent: int | str | Torrent) -> TorrentFile:
        """Download a ``.torrent`` file into memory.

        The files checked were 22 to 388 KB. To save one to disk without holding it in
        memory, use ``download()``.

        Args:
            torrent: Torrent ID, info hash, or a ``Torrent``.

        Returns:
            The file's bytes and the file name the API suggests.

        Raises:
            NotFoundError: No torrent with this ID or hash.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.

        Example:
            ```python
            torrent_file = await client.torrents.file(torrent)
            Path(torrent_file.filename or "release.torrent").write_bytes(torrent_file.content)
            ```
        """
        response = await self._http.request_raw(
            "GET", f"/anime/torrents/{_torrent_key(torrent)}/file"
        )
        return TorrentFile(filename=_suggested_filename(response), content=response.content)

    async def download(self, torrent: int | str | Torrent, *, path: str | os.PathLike[str]) -> Path:
        """Download a ``.torrent`` file to disk, streaming it in chunks.

        The file is written to a temporary ``<name>.part`` next to the target and renamed
        only once complete, so a failed download never leaves a truncated ``.torrent``
        behind. An existing file at the target path is overwritten.

        Args:
            torrent: Torrent ID, info hash, or a ``Torrent``.
            path: Where to save it: a file path, or an existing directory — then the file is
                named as the API suggests (falling back to ``<id or hash>.torrent``).

        Returns:
            The path of the saved file.

        Raises:
            NotFoundError: No torrent with this ID or hash.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            OSError: The file couldn't be written.

        Example:
            ```python
            saved = await client.torrents.download(torrent, path="downloads/")
            print(saved)  # downloads/One Piece - AniLiberty.TOP [WEBRip 1080p][AVC][1-24].torrent
            ```
        """
        key = _torrent_key(torrent)
        target = Path(path)
        async with self._http.stream("GET", f"/anime/torrents/{key}/file") as response:
            if target.is_dir():
                target = target / (_suggested_filename(response) or f"{key}.torrent")
            partial = target.with_name(target.name + ".part")
            try:
                with partial.open("wb") as file:
                    async for chunk in response.aiter_bytes():
                        file.write(chunk)
            except BaseException:
                partial.unlink(missing_ok=True)
                raise
        partial.replace(target)
        return target

    async def rss(self, *, limit: int | None = None) -> str:
        """Get the RSS feed of the latest torrents, as XML text.

        The feed is meant for torrent clients and feed readers; each ``<item>`` has the
        torrent's hash (``<guid>``), ``<torrentId>``, ``<releaseId>`` and an ``<enclosure>``
        linking to the ``.torrent`` file. For the same data as models, use ``list()``.

        Args:
            limit: How many torrents to include. Omitted, the API includes 10.

        Returns:
            The RSS 2.0 document.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.

        Example:
            ```python
            xml = await client.torrents.rss(limit=10)
            print(xml[:60])  # <?xml version="1.0" encoding="UTF-8"?>...
            ```
        """
        response = await self._http.request_raw(
            "GET", "/anime/torrents/rss", params={"limit": limit} if limit is not None else None
        )
        return response.text

    async def rss_for_release(self, release: int | Release) -> str:
        """Get the RSS feed of a release's torrents, as XML text.

        Args:
            release: Release ID, or a ``Release`` (aliases don't work here, as in
                ``for_release()``).

        Returns:
            The RSS 2.0 document.

        Raises:
            TypeError: ``release`` is not an ``int`` or a ``Release``.
            NotFoundError: No release with this ID.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.

        Example:
            ```python
            xml = await client.torrents.rss_for_release(release)
            ```
        """
        response = await self._http.request_raw(
            "GET", f"/anime/torrents/rss/release/{numeric_release_id(release)}"
        )
        return response.text


def _torrent_key(torrent: int | str | Torrent) -> str:
    """Turn a torrent ID, hash or ``Torrent`` into the path segment, or raise."""
    if isinstance(torrent, Torrent):
        return str(torrent.id)
    return path_segment(torrent, what="torrent ID or hash")


def _suggested_filename(response: httpx.Response) -> str | None:
    """The file name from ``Content-Disposition``, made safe to use as a file name."""
    header = response.headers.get("Content-Disposition")
    if not header:
        return None
    message = Message()
    message["Content-Disposition"] = header
    name = message.get_filename()
    if not name:
        return None
    safe = _UNSAFE_FILENAME_CHARS.sub("_", name).strip(" .")
    return safe or None
