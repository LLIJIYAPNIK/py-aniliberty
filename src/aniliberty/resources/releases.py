"""``client.releases`` — the ``Аниме.Релизы`` tag of the spec."""

from __future__ import annotations

import builtins
from collections.abc import AsyncIterator, Sequence

from aniliberty._http import HttpClient
from aniliberty.models.release import Release, ReleaseMember
from aniliberty.models.view import EpisodeView
from aniliberty.pagination import Page, iterate_pages
from aniliberty.resources._base import BaseResource, path_segment
from aniliberty.resources.ratings import RatingsResource


class ReleasesResource(BaseResource):
    """Anime releases, available as ``client.releases``.

    For filtering and sorting the whole catalog, see ``client.catalog``; this namespace
    covers single releases and the ready-made selections.

    ``limit`` on every method here must be between 1 and 50 — the API answers anything else
    with a 422, raised as ``ValidationError`` (see ``docs/api-notes.md``).

    Attributes:
        ratings: The logged-in user's own scores of releases (needs a session).
    """

    ENDPOINTS = (
        ("GET", "/anime/releases/latest"),
        ("GET", "/anime/releases/random"),
        ("GET", "/anime/releases/recommended"),
        ("GET", "/anime/releases/list"),
        ("GET", "/anime/releases/{idOrAlias}"),
        ("GET", "/anime/releases/{idOrAlias}/members"),
        ("GET", "/anime/releases/{idOrAlias}/episodes/timecodes"),
    )

    def __init__(self, http: HttpClient) -> None:
        super().__init__(http)
        self.ratings = RatingsResource(http)

    async def latest(self, *, limit: int | None = None) -> builtins.list[Release]:
        """Get the latest releases — the ones that got new episodes most recently.

        Args:
            limit: How many releases to return, 1 to 50. Omitted, the API picks the number.

        Returns:
            The releases, with ``genres`` filled in.

        Raises:
            ValidationError: ``limit`` is out of range.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Release``.

        Example:
            ```python
            for release in await client.releases.latest(limit=5):
                print(release.fresh_at, release.name.main)
            ```
        """
        return await self._get(
            "/anime/releases/latest", builtins.list[Release], params={"limit": limit}
        )

    async def random(self, *, limit: int | None = None) -> builtins.list[Release]:
        """Get random releases.

        Args:
            limit: How many releases to return, 1 to 50.

        Returns:
            The releases, with ``genres`` and ``background_covers`` filled in.

        Raises:
            ValidationError: ``limit`` is out of range.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Release``.

        Example:
            ```python
            [release] = await client.releases.random(limit=1)
            print(release.name.main, release.year)
            ```
        """
        return await self._get(
            "/anime/releases/random", builtins.list[Release], params={"limit": limit}
        )

    async def recommended(
        self, *, release_id: int | None = None, limit: int | None = None
    ) -> builtins.list[Release]:
        """Get recommended releases, optionally ones similar to a given release.

        Args:
            release_id: ID of the release to base recommendations on. Without it, the API
                returns general recommendations.
            limit: How many releases to return, 1 to 50.

        Returns:
            The releases, with ``genres`` filled in.

        Raises:
            ValidationError: ``limit`` is out of range.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Release``.

        Example:
            ```python
            similar = await client.releases.recommended(release_id=release.id, limit=5)
            ```
        """
        return await self._get(
            "/anime/releases/recommended",
            builtins.list[Release],
            params={"release_id": release_id, "limit": limit},
        )

    async def list(
        self,
        *,
        ids: Sequence[int] | None = None,
        aliases: Sequence[str] | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Page[Release]:
        """Get several releases at once by their IDs and/or aliases.

        Releases given both by ID and by alias are returned once. The order of the result
        doesn't follow the order of ``ids``/``aliases``. To fetch all pages, use
        ``iter_list()``.

        Args:
            ids: Release IDs.
            aliases: Release aliases.
            page: Page number, starting at 1.
            limit: Page size, 1 to 50.

        Returns:
            One page of releases, with ``genres``, ``members`` and ``sponsors`` filled in.

        Raises:
            ValueError: Neither ``ids`` nor ``aliases`` was given (the API requires one).
            ValidationError: ``page`` or ``limit`` is out of range.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Release``.

        Example:
            ```python
            page = await client.releases.list(ids=[10172, 10297], aliases=["sousou-no-frieren"])
            for release in page.items:
                print(release.id, release.name.main)
            ```
        """
        if not ids and not aliases:
            raise ValueError("Pass ids, aliases, or both")
        return await self._get(
            "/anime/releases/list",
            Page[Release],
            params={"ids": ids, "aliases": aliases, "page": page, "limit": limit},
        )

    def iter_list(
        self,
        *,
        ids: Sequence[int] | None = None,
        aliases: Sequence[str] | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[Release]:
        """Iterate over all releases matching ``ids``/``aliases``, fetching page by page.

        Same as calling ``list()`` with ``page=1, 2, ...`` until the last page; the next page
        is requested only once the current one has been consumed.

        Args:
            ids: Release IDs.
            aliases: Release aliases.
            limit: Page size, 1 to 50 — affects how many requests are made, not the result.

        Returns:
            An async iterator over the releases.

        Raises:
            ValueError: Neither ``ids`` nor ``aliases`` was given — raised right away, not
                when iteration starts.

        Example:
            ```python
            async for release in client.releases.iter_list(ids=favorite_ids, limit=50):
                print(release.name.main)
            ```
        """
        if not ids and not aliases:
            raise ValueError("Pass ids, aliases, or both")

        async def fetch(page: int) -> Page[Release]:
            return await self.list(ids=ids, aliases=aliases, page=page, limit=limit)

        return iterate_pages(fetch)

    async def get(self, id_or_alias: int | str) -> Release:
        """Get one release by its ID or alias.

        Args:
            id_or_alias: Release ID (``10297``) or alias (``"sousou-no-frieren"``).

        Returns:
            The release, with ``genres``, ``members``, ``sponsors`` and
            ``background_covers`` filled in.

        Raises:
            NotFoundError: No release with this ID or alias.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Release``.

        Example:
            ```python
            release = await client.releases.get("tensei-shitara-ken-deshita-2nd-season")
            print(release.name.main, release.episodes_total)
            ```
        """
        return await self._get(
            f"/anime/releases/{path_segment(id_or_alias, what='release ID or alias')}", Release
        )

    async def members(self, id_or_alias: int | str) -> builtins.list[ReleaseMember]:
        """Get the people who worked on a release (voice actors, translators, ...).

        Args:
            id_or_alias: Release ID or alias.

        Returns:
            The release's members.

        Raises:
            NotFoundError: No release with this ID or alias.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``ReleaseMember``.

        Example:
            ```python
            for member in await client.releases.members(10297):
                print(member.nickname, member.role.description if member.role else "")
            ```
        """
        return await self._get(
            f"/anime/releases/{path_segment(id_or_alias, what='release ID or alias')}/members",
            builtins.list[ReleaseMember],
        )

    async def timecodes(self, id_or_alias: int | str) -> builtins.list[EpisodeView]:
        """Get the logged-in user's watch records of a release's episodes. Needs a session.

        Records appear about a minute after ``client.me.views.save_timecodes()``.

        Args:
            id_or_alias: Release ID or alias.

        Returns:
            One record per episode the user has started; empty if none.

        Raises:
            NotFoundError: No release with this ID or alias.
            AuthRequiredError: No valid session.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``EpisodeView``.

        Example:
            ```python
            watched = {v.release_episode_id for v in await client.releases.timecodes(9839)
                       if v.is_watched}
            ```
        """
        segment = path_segment(id_or_alias, what="release ID or alias")
        return await self._get(
            f"/anime/releases/{segment}/episodes/timecodes", builtins.list[EpisodeView]
        )
