"""``client.genres`` — the ``Аниме.Жанры`` tag of the spec."""

from __future__ import annotations

import builtins
from collections.abc import AsyncIterator

from aniliberty.models.genre import Genre
from aniliberty.models.release import Release
from aniliberty.pagination import Page, iterate_pages
from aniliberty.resources._base import BaseResource


class GenresResource(BaseResource):
    """Anime genres with their images and release counts, available as ``client.genres``.

    To filter the catalog by several genres at once, use ``client.catalog.releases(genres=...)``;
    ``releases()`` here lists the releases of one genre.
    """

    ENDPOINTS = (
        ("GET", "/anime/genres"),
        ("GET", "/anime/genres/{genreId}"),
        ("GET", "/anime/genres/random"),
        ("GET", "/anime/genres/{genreId}/releases"),
    )

    async def list(self, *, refresh: bool = False) -> builtins.list[Genre]:
        """Get all genres.

        Args:
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            Every genre, with ``image`` and ``total_releases`` filled in.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Genre``.

        Example:
            ```python
            for genre in await client.genres.list():
                print(genre.name, genre.total_releases)
            ```
        """
        return await self._get("/anime/genres", builtins.list[Genre], cache=True, refresh=refresh)

    async def get(self, genre: int | Genre, *, refresh: bool = False) -> Genre:
        """Get one genre.

        Args:
            genre: Genre ID, or a ``Genre`` (e.g. from ``client.catalog.references.genres()``,
                which has no image) to fetch its full data.
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            The genre, with ``image`` and ``total_releases``.

        Raises:
            NotFoundError: No genre with this ID.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Genre``.

        Example:
            ```python
            genre = await client.genres.get(14)
            print(genre.name, genre.total_releases)
            ```
        """
        return await self._get(
            f"/anime/genres/{_genre_id(genre)}", Genre, cache=True, refresh=refresh
        )

    async def random(self, *, limit: int | None = None) -> builtins.list[Genre]:
        """Get random genres.

        Args:
            limit: How many genres to return. A value outside 1..(number of genres) isn't an
                error: the API returns all genres instead.

        Returns:
            The genres, in random order.

        Raises:
            ValidationError: ``limit`` isn't a number.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Genre``.

        Example:
            ```python
            for genre in await client.genres.random(limit=3):
                print(genre.name)
            ```
        """
        return await self._get(
            "/anime/genres/random", builtins.list[Genre], params={"limit": limit}
        )

    async def releases(
        self,
        genre: int | Genre,
        *,
        page: int | None = None,
        limit: int | None = None,
        refresh: bool = False,
    ) -> Page[Release]:
        """Get one page of the releases of a genre.

        The order is the API's own (neither by update date nor by year). For sorting and for
        combining genres with other filters, use ``client.catalog.releases(genres=[...])``.

        Args:
            genre: Genre ID or ``Genre``.
            page: Page number, starting at 1. The API treats 0 and negative numbers as 1.
            limit: Page size, 1 to **30** here (not 50 as in the catalog). Omitted, the API
                uses 15.
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            One page of releases, with ``genres`` filled in.

        Raises:
            NotFoundError: No genre with this ID.
            ValidationError: ``limit`` is out of range.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Release``.

        Example:
            ```python
            page = await client.genres.releases(14, limit=30)
            print(f"{page.total} releases in this genre")
            ```
        """
        return await self._get(
            f"/anime/genres/{_genre_id(genre)}/releases",
            Page[Release],
            params={"page": page, "limit": limit},
            cache=True,
            refresh=refresh,
        )

    def iter_releases(
        self,
        genre: int | Genre,
        *,
        limit: int | None = None,
        refresh: bool = False,
    ) -> AsyncIterator[Release]:
        """Iterate over all releases of a genre, fetching page by page.

        Args:
            genre: Genre ID or ``Genre``.
            limit: Page size, 1 to 30 — affects how many requests are made, not the result.
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            An async iterator over the releases.

        Raises:
            TypeError: ``genre`` isn't an ID or a ``Genre`` — raised right away.

        Example:
            ```python
            async for release in client.genres.iter_releases(14, limit=30):
                print(release.name.main)
            ```
        """
        genre_id = _genre_id(genre)

        async def fetch(page: int) -> Page[Release]:
            return await self.releases(genre_id, page=page, limit=limit, refresh=refresh)

        return iterate_pages(fetch)


def _genre_id(genre: int | Genre) -> int:
    """Turn a genre ID or ``Genre`` into the ID, or raise."""
    genre_id = genre.id if isinstance(genre, Genre) else genre
    if isinstance(genre_id, bool) or not isinstance(genre_id, int):
        raise TypeError(f"Expected a genre ID or a Genre, got {genre!r}")
    return genre_id
