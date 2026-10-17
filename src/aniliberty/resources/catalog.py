"""``client.catalog`` — the ``Аниме.Каталог`` tags of the spec."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any, get_args

from aniliberty._http import HttpClient
from aniliberty.models.catalog import (
    AgeRatingValue,
    CatalogSorting,
    ProductionStatus,
    PublishStatus,
    ReleaseType,
    Season,
    SortingOption,
)
from aniliberty.models.common import ValueDescription
from aniliberty.models.genre import Genre
from aniliberty.models.release import AgeRating, Release
from aniliberty.pagination import Page, iterate_pages
from aniliberty.resources._base import BaseResource
from aniliberty.resources._filters import enum_value, enum_values, genre_ids


class CatalogReferencesResource(BaseResource):
    """Values the catalog filters accept, available as ``client.catalog.references``.

    Each method returns the list the site shows in its catalog filters. Use them instead of
    hardcoding values: the ``value`` (or ``id`` for genres, the number for years) of an item is
    exactly what the corresponding catalog filter takes.

    The lists are small and change rarely — fetching them once per program run is enough.

    Example:
        ```python
        genres = await client.catalog.references.genres()
        action = next(g for g in genres if g.name == "Экшен")
        print(action.id)
        ```
    """

    ENDPOINTS = (
        ("GET", "/anime/catalog/references/age-ratings"),
        ("GET", "/anime/catalog/references/genres"),
        ("GET", "/anime/catalog/references/production-statuses"),
        ("GET", "/anime/catalog/references/publish-statuses"),
        ("GET", "/anime/catalog/references/seasons"),
        ("GET", "/anime/catalog/references/sorting"),
        ("GET", "/anime/catalog/references/types"),
        ("GET", "/anime/catalog/references/years"),
    )

    async def genres(self, *, refresh: bool = False) -> list[Genre]:
        """Get the genres the catalog can be filtered by.

        Args:
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            Genres with ``id`` and ``name`` only — ``image`` and ``total_releases`` are
            ``None`` here, this list doesn't include them.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Genre``.

        Example:
            ```python
            genres = await client.catalog.references.genres()
            action = next(genre for genre in genres if genre.name == "Экшен")
            page = await client.catalog.releases(genres=[action])
            ```
        """
        return await self._get(
            "/anime/catalog/references/genres", list[Genre], cache=True, refresh=refresh
        )

    async def types(self, *, refresh: bool = False) -> list[ValueDescription[str]]:
        """Get the release types, e.g. ``value="TV"``, ``description="ТВ"``.

        Args:
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            The release types.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``ValueDescription``.

        Example:
            ```python
            types = await client.catalog.references.types()
            print([t.value for t in types])  # ['TV', 'ONA', 'WEB', ...]
            ```
        """
        return await self._get(
            "/anime/catalog/references/types",
            list[ValueDescription[str]],
            cache=True,
            refresh=refresh,
        )

    async def seasons(self, *, refresh: bool = False) -> list[ValueDescription[str]]:
        """Get the seasons, e.g. ``value="winter"``, ``description="Зима"``.

        Args:
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            The seasons.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``ValueDescription``.

        Example:
            ```python
            for season in await client.catalog.references.seasons():
                print(season.value, season.description)
            ```
        """
        return await self._get(
            "/anime/catalog/references/seasons",
            list[ValueDescription[str]],
            cache=True,
            refresh=refresh,
        )

    async def years(self, *, refresh: bool = False) -> list[int]:
        """Get the years that have releases in the catalog, oldest first.

        Only years with at least one release are listed, so the range can have gaps.

        Args:
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            The years.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response wasn't a list of integers.

        Example:
            ```python
            years = await client.catalog.references.years()
            print(years[0], years[-1])  # the oldest and the newest year
            ```
        """
        return await self._get(
            "/anime/catalog/references/years", list[int], cache=True, refresh=refresh
        )

    async def age_ratings(self, *, refresh: bool = False) -> list[AgeRating]:
        """Get the age ratings, e.g. ``value="R16_PLUS"``, ``label="16+"``.

        Args:
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            The age ratings (``is_adult`` is ``None`` here — this list doesn't include it).

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``AgeRating``.

        Example:
            ```python
            for rating in await client.catalog.references.age_ratings():
                print(rating.value, rating.label)
            ```
        """
        return await self._get(
            "/anime/catalog/references/age-ratings", list[AgeRating], cache=True, refresh=refresh
        )

    async def publish_statuses(self, *, refresh: bool = False) -> list[ValueDescription[str]]:
        """Get the airing statuses, e.g. ``value="IS_ONGOING"``, ``description="Онгоинг"``.

        Args:
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            The publish statuses.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``ValueDescription``.

        Example:
            ```python
            statuses = await client.catalog.references.publish_statuses()
            ongoing = next(s for s in statuses if s.value == "IS_ONGOING")
            page = await client.catalog.releases(publish_statuses=[ongoing])
            ```
        """
        return await self._get(
            "/anime/catalog/references/publish-statuses",
            list[ValueDescription[str]],
            cache=True,
            refresh=refresh,
        )

    async def production_statuses(self, *, refresh: bool = False) -> list[ValueDescription[str]]:
        """Get the dubbing statuses, e.g. ``value="IS_IN_PRODUCTION"``.

        Args:
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            The production statuses.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``ValueDescription``.

        Example:
            ```python
            for status in await client.catalog.references.production_statuses():
                print(status.value, status.description)
            ```
        """
        return await self._get(
            "/anime/catalog/references/production-statuses",
            list[ValueDescription[str]],
            cache=True,
            refresh=refresh,
        )

    async def sorting(self, *, refresh: bool = False) -> list[SortingOption]:
        """Get the ways the catalog can be sorted, e.g. ``value="FRESH_AT_DESC"``.

        Args:
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            The sorting options.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``SortingOption``.

        Example:
            ```python
            for option in await client.catalog.references.sorting():
                print(option.value, option.label)
            ```
        """
        return await self._get(
            "/anime/catalog/references/sorting", list[SortingOption], cache=True, refresh=refresh
        )


class CatalogResource(BaseResource):
    """The release catalog with filters and sorting, available as ``client.catalog``.

    How the filters combine (checked against the live API, see ``docs/api-notes.md``):

    - ``genres``: a release must have **all** of the given genres (AND);
    - ``types``, ``seasons``, ``age_ratings``, ``publish_statuses``,
      ``production_statuses``: **any** of the given values (OR);
    - different filters: all of them must match (AND);
    - ``year_from``/``year_to``: inclusive on both ends;
    - ``search``: the same matching as ``client.app.search_releases()``, and likewise
      capped at about 20 matches in total, whatever the other filters and the page size.

    Without ``sorting``, releases come in ``"FRESH_AT_DESC"`` order (recently updated first).

    Attributes:
        references: Values the catalog filters accept.
    """

    ENDPOINTS = (("GET", "/anime/catalog/releases"),)

    def __init__(self, http: HttpClient) -> None:
        super().__init__(http)
        self.references = CatalogReferencesResource(http)

    async def releases(
        self,
        *,
        genres: Sequence[int | Genre] | None = None,
        types: Sequence[ReleaseType | ValueDescription[str]] | None = None,
        seasons: Sequence[Season | ValueDescription[str]] | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        search: str | None = None,
        sorting: CatalogSorting | SortingOption | None = None,
        age_ratings: Sequence[AgeRatingValue | ValueDescription[str]] | None = None,
        publish_statuses: Sequence[PublishStatus | ValueDescription[str]] | None = None,
        production_statuses: Sequence[ProductionStatus | ValueDescription[str]] | None = None,
        page: int | None = None,
        limit: int | None = None,
        refresh: bool = False,
    ) -> Page[Release]:
        """Get one page of catalog releases matching the filters.

        Every filter is optional; without any, this is the whole catalog. Values can be
        passed as plain strings/IDs or as the items ``client.catalog.references`` returns.
        To go through all pages, use ``iter_releases()``.

        Args:
            genres: Genre IDs (or ``Genre`` objects); a release must have all of them.
            types: Release types, e.g. ``["TV", "MOVIE"]``; any of them.
            seasons: Seasons, e.g. ``["winter"]``; any of them.
            year_from: Earliest release year, inclusive.
            year_to: Latest release year, inclusive.
            search: Text to search in names (capped at about 20 matches by the API).
            sorting: Sort order, e.g. ``"RATING_DESC"``. Default: ``"FRESH_AT_DESC"``.
            age_ratings: Age ratings, e.g. ``["R16_PLUS"]``; any of them.
            publish_statuses: ``"IS_ONGOING"`` and/or ``"IS_NOT_ONGOING"``.
            production_statuses: ``"IS_IN_PRODUCTION"`` and/or ``"IS_NOT_IN_PRODUCTION"``.
            page: Page number, starting at 1. A page past the last one is empty.
            limit: Page size, 1 to 50.
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            One page of releases, with ``genres`` filled in.

        Raises:
            ValueError: A filter value isn't one the API knows, or ``year_from`` is after
                ``year_to``. The API itself would silently return no releases (or ignore
                the filter) instead of reporting these, so they are checked here.
            TypeError: A list filter got a single string (``types="TV"``) or a value of
                the wrong type.
            ValidationError: ``page`` or ``limit`` is out of range.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Release``.

        Example:
            ```python
            page = await client.catalog.releases(
                genres=[14], types=["TV"], year_from=2020, sorting="RATING_DESC", limit=25
            )
            print(f"{page.total} releases, page 1 of {page.total_pages}")
            ```
        """
        params = _catalog_params(
            genres=genres,
            types=types,
            seasons=seasons,
            year_from=year_from,
            year_to=year_to,
            search=search,
            sorting=sorting,
            age_ratings=age_ratings,
            publish_statuses=publish_statuses,
            production_statuses=production_statuses,
        )
        return await self._fetch_page(params, page=page, limit=limit, refresh=refresh)

    def iter_releases(
        self,
        *,
        genres: Sequence[int | Genre] | None = None,
        types: Sequence[ReleaseType | ValueDescription[str]] | None = None,
        seasons: Sequence[Season | ValueDescription[str]] | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        search: str | None = None,
        sorting: CatalogSorting | SortingOption | None = None,
        age_ratings: Sequence[AgeRatingValue | ValueDescription[str]] | None = None,
        publish_statuses: Sequence[PublishStatus | ValueDescription[str]] | None = None,
        production_statuses: Sequence[ProductionStatus | ValueDescription[str]] | None = None,
        limit: int | None = None,
        refresh: bool = False,
    ) -> AsyncIterator[Release]:
        """Iterate over all catalog releases matching the filters, fetching page by page.

        Takes the same filters as ``releases()``. The next page is requested only once the
        current one has been consumed, so breaking out of the loop early stops the requests.
        The whole catalog is a couple of thousand releases — iterate all of it only when you
        really need everything.

        Args:
            genres: See ``releases()``.
            types: See ``releases()``.
            seasons: See ``releases()``.
            year_from: See ``releases()``.
            year_to: See ``releases()``.
            search: See ``releases()``.
            sorting: See ``releases()``.
            age_ratings: See ``releases()``.
            publish_statuses: See ``releases()``.
            production_statuses: See ``releases()``.
            limit: Page size, 1 to 50 — affects how many requests are made, not the result.
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            An async iterator over the releases.

        Raises:
            ValueError: Invalid filter values — raised right away, not when iteration starts.
            TypeError: A list filter got a single string or a value of the wrong type.

        Example:
            ```python
            async for release in client.catalog.iter_releases(types=["MOVIE"], limit=50):
                print(release.year, release.name.main)
            ```
        """
        params = _catalog_params(
            genres=genres,
            types=types,
            seasons=seasons,
            year_from=year_from,
            year_to=year_to,
            search=search,
            sorting=sorting,
            age_ratings=age_ratings,
            publish_statuses=publish_statuses,
            production_statuses=production_statuses,
        )

        async def fetch(page: int) -> Page[Release]:
            return await self._fetch_page(params, page=page, limit=limit, refresh=refresh)

        return iterate_pages(fetch)

    async def _fetch_page(
        self, params: dict[str, Any], *, page: int | None, limit: int | None, refresh: bool
    ) -> Page[Release]:
        return await self._get(
            "/anime/catalog/releases",
            Page[Release],
            params={**params, "page": page, "limit": limit},
            cache=True,
            refresh=refresh,
        )


def _catalog_params(
    *,
    genres: Sequence[int | Genre] | None,
    types: Sequence[str | ValueDescription[str]] | None,
    seasons: Sequence[str | ValueDescription[str]] | None,
    year_from: int | None,
    year_to: int | None,
    search: str | None,
    sorting: str | SortingOption | None,
    age_ratings: Sequence[str | ValueDescription[str]] | None,
    publish_statuses: Sequence[str | ValueDescription[str]] | None,
    production_statuses: Sequence[str | ValueDescription[str]] | None,
) -> dict[str, Any]:
    """Validate the filters and arrange them the way ``build_query`` turns into ``f[...]``."""
    for name, year in (("year_from", year_from), ("year_to", year_to)):
        if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
            raise TypeError(f"{name} must be an int, got {year!r}")
    if year_from is not None and year_to is not None and year_from > year_to:
        raise ValueError(f"year_from ({year_from}) is after year_to ({year_to})")
    sorting_value = (
        None if sorting is None else enum_value("sorting", sorting, get_args(CatalogSorting))
    )
    return {
        "f": {
            "genres": genre_ids(genres),
            "types": enum_values("types", types, get_args(ReleaseType)),
            "seasons": enum_values("seasons", seasons, get_args(Season)),
            "years": {"from_year": year_from, "to_year": year_to},
            "search": search,
            "sorting": sorting_value,
            "age_ratings": enum_values("age_ratings", age_ratings, get_args(AgeRatingValue)),
            "publish_statuses": enum_values(
                "publish_statuses", publish_statuses, get_args(PublishStatus)
            ),
            "production_statuses": enum_values(
                "production_statuses", production_statuses, get_args(ProductionStatus)
            ),
        }
    }
