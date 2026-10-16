"""``client.me.favorites`` — the ``Аккаунты.Пользователи.Мое.Избранное`` tags of the spec."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any, get_args

from aniliberty._http import HttpClient
from aniliberty.models.catalog import AgeRatingValue, ReleaseType, SortingOption
from aniliberty.models.common import ValueDescription
from aniliberty.models.genre import Genre
from aniliberty.models.release import Release
from aniliberty.models.user import FavoritesSorting
from aniliberty.pagination import Page, iterate_pages
from aniliberty.resources._base import BaseResource
from aniliberty.resources._filters import (
    enum_value,
    enum_values,
    genre_ids,
    release_ids,
    year_list,
)
from aniliberty.resources._lists import _OwnListReferencesResource

_PATH = "/accounts/users/me/favorites"


class FavoritesReferencesResource(_OwnListReferencesResource):
    """Values the favorites filters accept, available as ``client.me.favorites.references``.

    Unlike ``client.catalog.references``, the lists only contain what occurs in the user's
    own favorites: the genres, types, years and age ratings of the releases added there. With
    empty favorites they are empty — except ``sorting()``, which is always the full list.
    """

    ENDPOINTS = (
        ("GET", "/accounts/users/me/favorites/references/age-ratings"),
        ("GET", "/accounts/users/me/favorites/references/genres"),
        ("GET", "/accounts/users/me/favorites/references/sorting"),
        ("GET", "/accounts/users/me/favorites/references/types"),
        ("GET", "/accounts/users/me/favorites/references/years"),
    )
    _REFERENCES_PATH = f"{_PATH}/references"

    async def sorting(self) -> list[SortingOption]:
        """Get the ways favorites can be sorted, e.g. ``value="CREATED_AT_DESC"``.

        Returns:
            All sorting options, whatever is in favorites.

        Raises:
            AuthRequiredError: No valid session.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``SortingOption``.

        Example:
            ```python
            for option in await client.me.favorites.references.sorting():
                print(option.value, option.label)
            ```
        """
        return await self._get(f"{_PATH}/references/sorting", list[SortingOption])


class FavoritesResource(BaseResource):
    """The logged-in user's favorite releases, available as ``client.me.favorites``.

    Needs a session (``client.auth.login()`` or ``AniLiberty(token=...)``); without a valid
    one every method raises ``AuthRequiredError``.

    The API checks little here (see ``docs/api-notes.md``): ``add()`` accepts IDs of releases
    that don't exist — they end up in ``ids()``, though never in ``releases()`` — and adding a
    release twice or removing one that isn't there is silently a no-op.

    Attributes:
        references: Values the favorites filters accept.
    """

    ENDPOINTS = (
        ("GET", "/accounts/users/me/favorites/ids"),
        ("GET", "/accounts/users/me/favorites/releases"),
        ("POST", "/accounts/users/me/favorites"),
        ("DELETE", "/accounts/users/me/favorites"),
    )

    def __init__(self, http: HttpClient) -> None:
        super().__init__(http)
        self.references = FavoritesReferencesResource(http)

    async def ids(self) -> list[int]:
        """Get the IDs of all releases in favorites, in the order they were added.

        Cheaper than ``releases()`` for checking whether a release is a favorite.

        Returns:
            Release IDs.

        Raises:
            AuthRequiredError: No valid session.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response wasn't a list of integers.

        Example:
            ```python
            if release.id in await client.me.favorites.ids():
                print("already a favorite")
            ```
        """
        return await self._get(f"{_PATH}/ids", list[int])

    async def add(self, *releases: int | Release) -> list[int]:
        """Add releases to favorites.

        Args:
            *releases: Release IDs or ``Release`` objects, one or more. Releases already in
                favorites are skipped.

        Returns:
            IDs of all releases in favorites afterwards, like ``ids()``.

        Raises:
            ValueError: No releases given.
            TypeError: A value is neither an ``int`` nor a ``Release``.
            AuthRequiredError: No valid session.
            APIError: The API answered with another error.
            TransportError: The request failed without a response. Not retried: it's a
                ``POST``, though adding again would do no harm.
            ResponseParseError: The response wasn't a list of integers.

        Example:
            ```python
            await client.me.favorites.add(9839, release)
            ```
        """
        body = [{"release_id": release_id} for release_id in release_ids(releases)]
        payload = await self._http.request("POST", _PATH, json=body)
        return self._parse(payload, list[int], path=_PATH)

    async def remove(self, *releases: int | Release) -> list[int]:
        """Remove releases from favorites.

        Args:
            *releases: Release IDs or ``Release`` objects, one or more. Releases that aren't
                in favorites are skipped.

        Returns:
            IDs of the releases left in favorites, like ``ids()``.

        Raises:
            ValueError: No releases given.
            TypeError: A value is neither an ``int`` nor a ``Release``.
            AuthRequiredError: No valid session.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response wasn't a list of integers.

        Example:
            ```python
            left = await client.me.favorites.remove(9839)
            ```
        """
        body = [{"release_id": release_id} for release_id in release_ids(releases)]
        payload = await self._http.request("DELETE", _PATH, json=body)
        return self._parse(payload, list[int], path=_PATH)

    async def releases(
        self,
        *,
        genres: Sequence[int | Genre] | None = None,
        types: Sequence[ReleaseType | ValueDescription[str]] | None = None,
        years: Sequence[int] | None = None,
        search: str | None = None,
        sorting: FavoritesSorting | SortingOption | None = None,
        age_ratings: Sequence[AgeRatingValue | ValueDescription[str]] | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Page[Release]:
        """Get one page of favorite releases matching the filters.

        The filters combine like the catalog's: a release must have **all** of ``genres``
        and **any** of the ``types``, ``years`` and ``age_ratings``; different filters must
        all match. To go through all pages, use ``iter_releases()``.

        Args:
            genres: Genre IDs (or ``Genre`` objects); a release must have all of them.
            types: Release types, e.g. ``["TV", "MOVIE"]``; any of them.
            years: Release years; any of them. A range works too: ``range(2020, 2026)``.
            search: Text to search in names.
            sorting: Sort order. Default: ``"CREATED_AT_DESC"`` (added to favorites most
                recently first). ``"RATING_*"`` sorts by how many users have the release in
                favorites.
            age_ratings: Age ratings, e.g. ``["R16_PLUS"]``; any of them.
            page: Page number, starting at 1. A page past the last one is empty.
            limit: Page size, 1 to 50. Default: 25.

        Returns:
            One page of releases, with ``genres`` and ``episodes`` filled in.

        Raises:
            ValueError: A filter value isn't one the API knows (it would silently return
                nothing or ignore the filter instead).
            TypeError: A list filter got a single value (``types="TV"``, ``years=2024``) or
                a value of the wrong type.
            AuthRequiredError: No valid session.
            ValidationError: ``page`` or ``limit`` is out of range.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Release``.

        Example:
            ```python
            page = await client.me.favorites.releases(types=["TV"], sorting="YEAR_DESC")
            for release in page.items:
                print(release.year, release.name.main)
            ```
        """
        params = _favorites_params(
            genres=genres,
            types=types,
            years=years,
            search=search,
            sorting=sorting,
            age_ratings=age_ratings,
        )
        return await self._fetch_page(params, page=page, limit=limit)

    def iter_releases(
        self,
        *,
        genres: Sequence[int | Genre] | None = None,
        types: Sequence[ReleaseType | ValueDescription[str]] | None = None,
        years: Sequence[int] | None = None,
        search: str | None = None,
        sorting: FavoritesSorting | SortingOption | None = None,
        age_ratings: Sequence[AgeRatingValue | ValueDescription[str]] | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[Release]:
        """Iterate over all favorite releases matching the filters, fetching page by page.

        Takes the same filters as ``releases()``; the next page is requested only once the
        current one has been consumed.

        Args:
            genres: See ``releases()``.
            types: See ``releases()``.
            years: See ``releases()``.
            search: See ``releases()``.
            sorting: See ``releases()``.
            age_ratings: See ``releases()``.
            limit: Page size, 1 to 50 — affects how many requests are made, not the result.

        Returns:
            An async iterator over the releases.

        Raises:
            ValueError: Invalid filter values — raised right away, not when iteration starts.
            TypeError: A list filter got a single value or a value of the wrong type.

        Example:
            ```python
            async for release in client.me.favorites.iter_releases(limit=50):
                print(release.name.main)
            ```
        """
        params = _favorites_params(
            genres=genres,
            types=types,
            years=years,
            search=search,
            sorting=sorting,
            age_ratings=age_ratings,
        )

        async def fetch(page: int) -> Page[Release]:
            return await self._fetch_page(params, page=page, limit=limit)

        return iterate_pages(fetch)

    async def _fetch_page(
        self, params: dict[str, Any], *, page: int | None, limit: int | None
    ) -> Page[Release]:
        return await self._get(
            f"{_PATH}/releases", Page[Release], params={**params, "page": page, "limit": limit}
        )


def _favorites_params(
    *,
    genres: Sequence[int | Genre] | None,
    types: Sequence[str | ValueDescription[str]] | None,
    years: Sequence[int] | None,
    search: str | None,
    sorting: str | SortingOption | None,
    age_ratings: Sequence[str | ValueDescription[str]] | None,
) -> dict[str, Any]:
    """Validate the filters and arrange them the way ``build_query`` turns into ``f[...]``."""
    return {
        "f": {
            "genres": genre_ids(genres),
            "types": enum_values("types", types, get_args(ReleaseType)),
            "years": year_list(years),
            "search": search,
            "sorting": (
                None
                if sorting is None
                else enum_value("sorting", sorting, get_args(FavoritesSorting))
            ),
            "age_ratings": enum_values("age_ratings", age_ratings, get_args(AgeRatingValue)),
        }
    }
