"""``client.me.collections`` — the ``Аккаунты.Пользователи.Мое.Коллекции`` tags of the spec."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any, get_args

from aniliberty._http import HttpClient
from aniliberty.models.catalog import AgeRatingValue, ReleaseType
from aniliberty.models.common import ValueDescription
from aniliberty.models.genre import Genre
from aniliberty.models.release import Release
from aniliberty.models.user import CollectionItem, CollectionType
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

_PATH = "/accounts/users/me/collections"


class CollectionsReferencesResource(_OwnListReferencesResource):
    """Values the collections filters accept, available as ``client.me.collections.references``.

    The lists cover all the user's collections together — the API has no per-collection
    variant (a ``type_of_collection`` parameter is ignored). Collections can't be sorted, so
    unlike favorites there is no ``sorting()``.
    """

    ENDPOINTS = (
        ("GET", "/accounts/users/me/collections/references/age-ratings"),
        ("GET", "/accounts/users/me/collections/references/genres"),
        ("GET", "/accounts/users/me/collections/references/types"),
        ("GET", "/accounts/users/me/collections/references/years"),
    )
    _REFERENCES_PATH = f"{_PATH}/references"


class CollectionsResource(BaseResource):
    """The user's collections, available as ``client.me.collections``.

    There are five collections (``CollectionType``): ``"PLANNED"``, ``"WATCHED"``,
    ``"WATCHING"``, ``"POSTPONED"`` and ``"ABANDONED"``. A release is in at most one of them:
    adding it to another collection moves it there. Collections are separate from favorites.

    Needs a session (``client.auth.login()`` or ``AniLiberty(token=...)``); without a valid
    one every method raises ``AuthRequiredError``. As with favorites, the API accepts IDs of
    releases that don't exist, and removing a release that isn't in any collection is a
    no-op.

    Attributes:
        references: Values the collections filters accept.
    """

    ENDPOINTS = (
        ("GET", "/accounts/users/me/collections/ids"),
        ("GET", "/accounts/users/me/collections/releases"),
        ("POST", "/accounts/users/me/collections"),
        ("DELETE", "/accounts/users/me/collections"),
    )

    def __init__(self, http: HttpClient) -> None:
        super().__init__(http)
        self.references = CollectionsReferencesResource(http)

    async def ids(self) -> list[CollectionItem]:
        """Get every release in the collections, with the collection it's in.

        Returns:
            One item per release, in the order the releases were added.

        Raises:
            AuthRequiredError: No valid session.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``CollectionItem``.

        Example:
            ```python
            where = {item.release_id: item.collection for item in await client.me.collections.ids()}
            print(where.get(9839))  # e.g. "WATCHED", or None
            ```
        """
        return await self._get(f"{_PATH}/ids", list[CollectionItem])

    async def add(self, *releases: int | Release, to: CollectionType) -> list[CollectionItem]:
        """Put releases into a collection, moving them out of the one they were in.

        Args:
            *releases: Release IDs or ``Release`` objects, one or more.
            to: The collection, e.g. ``"WATCHING"``.

        Returns:
            Every release in the collections afterwards, like ``ids()``.

        Raises:
            ValueError: No releases given, or ``to`` isn't a collection type.
            TypeError: A release is neither an ``int`` nor a ``Release``.
            AuthRequiredError: No valid session.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``CollectionItem``.

        Example:
            ```python
            await client.me.collections.add(9839, release, to="WATCHING")
            await client.me.collections.add(9839, to="WATCHED")  # moved
            ```
        """
        collection = enum_value("collection", to, get_args(CollectionType))
        body = [
            {"release_id": release_id, "type_of_collection": collection}
            for release_id in release_ids(releases)
        ]
        payload = await self._http.request("POST", _PATH, json=body)
        return self._parse(payload, list[CollectionItem], path=_PATH)

    async def remove(self, *releases: int | Release) -> list[CollectionItem]:
        """Take releases out of whatever collection they are in.

        Args:
            *releases: Release IDs or ``Release`` objects, one or more.

        Returns:
            The releases left in the collections, like ``ids()``.

        Raises:
            ValueError: No releases given.
            TypeError: A release is neither an ``int`` nor a ``Release``.
            AuthRequiredError: No valid session.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``CollectionItem``.

        Example:
            ```python
            await client.me.collections.remove(9839)
            ```
        """
        body = [{"release_id": release_id} for release_id in release_ids(releases)]
        payload = await self._http.request("DELETE", _PATH, json=body)
        return self._parse(payload, list[CollectionItem], path=_PATH)

    async def releases(
        self,
        collection: CollectionType,
        *,
        genres: Sequence[int | Genre] | None = None,
        types: Sequence[ReleaseType | ValueDescription[str]] | None = None,
        years: Sequence[int] | None = None,
        search: str | None = None,
        age_ratings: Sequence[AgeRatingValue | ValueDescription[str]] | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Page[Release]:
        """Get one page of the releases in a collection, matching the filters.

        Releases come most recently added first; the API offers no other order. The filters
        combine like the favorites' ones: all of ``genres``, any of the ``types``, ``years``
        and ``age_ratings``. To go through all pages, use ``iter_releases()``.

        Args:
            collection: The collection, e.g. ``"PLANNED"``.
            genres: Genre IDs (or ``Genre`` objects); a release must have all of them.
            types: Release types, e.g. ``["TV", "MOVIE"]``; any of them.
            years: Release years; any of them. A range works too: ``range(2020, 2026)``.
            search: Text to search in names.
            age_ratings: Age ratings, e.g. ``["R16_PLUS"]``; any of them.
            page: Page number, starting at 1. A page past the last one is empty.
            limit: Page size, 1 to 50. Default: 25.

        Returns:
            One page of releases, with ``genres`` and ``episodes`` filled in.

        Raises:
            ValueError: ``collection`` or a filter value isn't one the API knows.
            TypeError: A list filter got a single value or a value of the wrong type.
            AuthRequiredError: No valid session.
            ValidationError: ``page`` or ``limit`` is out of range.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Release``.

        Example:
            ```python
            page = await client.me.collections.releases("WATCHING", types=["TV"])
            for release in page.items:
                print(release.name.main)
            ```
        """
        params = _collection_params(
            collection,
            genres=genres,
            types=types,
            years=years,
            search=search,
            age_ratings=age_ratings,
        )
        return await self._fetch_page(params, page=page, limit=limit)

    def iter_releases(
        self,
        collection: CollectionType,
        *,
        genres: Sequence[int | Genre] | None = None,
        types: Sequence[ReleaseType | ValueDescription[str]] | None = None,
        years: Sequence[int] | None = None,
        search: str | None = None,
        age_ratings: Sequence[AgeRatingValue | ValueDescription[str]] | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[Release]:
        """Iterate over all releases in a collection matching the filters, page by page.

        Takes the same arguments as ``releases()``; the next page is requested only once the
        current one has been consumed.

        Args:
            collection: See ``releases()``.
            genres: See ``releases()``.
            types: See ``releases()``.
            years: See ``releases()``.
            search: See ``releases()``.
            age_ratings: See ``releases()``.
            limit: Page size, 1 to 50 — affects how many requests are made, not the result.

        Returns:
            An async iterator over the releases.

        Raises:
            ValueError: Invalid ``collection`` or filter values — raised right away, not when
                iteration starts.
            TypeError: A list filter got a single value or a value of the wrong type.

        Example:
            ```python
            async for release in client.me.collections.iter_releases("WATCHED"):
                print(release.name.main)
            ```
        """
        params = _collection_params(
            collection,
            genres=genres,
            types=types,
            years=years,
            search=search,
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


def _collection_params(
    collection: str,
    *,
    genres: Sequence[int | Genre] | None,
    types: Sequence[str | ValueDescription[str]] | None,
    years: Sequence[int] | None,
    search: str | None,
    age_ratings: Sequence[str | ValueDescription[str]] | None,
) -> dict[str, Any]:
    """Validate the arguments and arrange them the way ``build_query`` sends them."""
    return {
        "type_of_collection": enum_value("collection", collection, get_args(CollectionType)),
        "f": {
            "genres": genre_ids(genres),
            "types": enum_values("types", types, get_args(ReleaseType)),
            "years": year_list(years),
            "search": search,
            "age_ratings": enum_values("age_ratings", age_ratings, get_args(AgeRatingValue)),
        },
    }
