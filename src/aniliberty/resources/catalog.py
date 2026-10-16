"""``client.catalog`` — the ``Аниме.Каталог`` tags of the spec."""

from __future__ import annotations

from aniliberty._http import HttpClient
from aniliberty.models.catalog import SortingOption
from aniliberty.models.common import ValueDescription
from aniliberty.models.genre import Genre
from aniliberty.models.release import AgeRating
from aniliberty.resources._base import BaseResource


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

    async def genres(self) -> list[Genre]:
        """Get the genres the catalog can be filtered by.

        Returns:
            Genres with ``id`` and ``name`` only — ``image`` and ``total_releases`` are
            ``None`` here, this list doesn't include them.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Genre``.
        """
        return await self._get("/anime/catalog/references/genres", list[Genre])

    async def types(self) -> list[ValueDescription[str]]:
        """Get the release types, e.g. ``value="TV"``, ``description="ТВ"``.

        Returns:
            The release types.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``ValueDescription``.
        """
        return await self._get("/anime/catalog/references/types", list[ValueDescription[str]])

    async def seasons(self) -> list[ValueDescription[str]]:
        """Get the seasons, e.g. ``value="winter"``, ``description="Зима"``.

        Returns:
            The seasons.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``ValueDescription``.
        """
        return await self._get("/anime/catalog/references/seasons", list[ValueDescription[str]])

    async def years(self) -> list[int]:
        """Get the years that have releases in the catalog, oldest first.

        Only years with at least one release are listed, so the range can have gaps.

        Returns:
            The years.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response wasn't a list of integers.
        """
        return await self._get("/anime/catalog/references/years", list[int])

    async def age_ratings(self) -> list[AgeRating]:
        """Get the age ratings, e.g. ``value="R16_PLUS"``, ``label="16+"``.

        Returns:
            The age ratings (``is_adult`` is ``None`` here — this list doesn't include it).

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``AgeRating``.
        """
        return await self._get("/anime/catalog/references/age-ratings", list[AgeRating])

    async def publish_statuses(self) -> list[ValueDescription[str]]:
        """Get the airing statuses, e.g. ``value="IS_ONGOING"``, ``description="Онгоинг"``.

        Returns:
            The publish statuses.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``ValueDescription``.
        """
        return await self._get(
            "/anime/catalog/references/publish-statuses", list[ValueDescription[str]]
        )

    async def production_statuses(self) -> list[ValueDescription[str]]:
        """Get the dubbing statuses, e.g. ``value="IS_IN_PRODUCTION"``.

        Returns:
            The production statuses.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``ValueDescription``.
        """
        return await self._get(
            "/anime/catalog/references/production-statuses", list[ValueDescription[str]]
        )

    async def sorting(self) -> list[SortingOption]:
        """Get the ways the catalog can be sorted, e.g. ``value="FRESH_AT_DESC"``.

        Returns:
            The sorting options.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``SortingOption``.
        """
        return await self._get("/anime/catalog/references/sorting", list[SortingOption])


class CatalogResource(BaseResource):
    """The release catalog, available as ``client.catalog``.

    Attributes:
        references: Values the catalog filters accept.
    """

    def __init__(self, http: HttpClient) -> None:
        super().__init__(http)
        self.references = CatalogReferencesResource(http)
