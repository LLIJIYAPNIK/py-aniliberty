"""Shared parts of the user's own release lists — favorites and collections (not public API)."""

from __future__ import annotations

from typing import ClassVar

from aniliberty.models.common import ValueDescription
from aniliberty.models.genre import Genre
from aniliberty.models.release import AgeRating
from aniliberty.resources._base import BaseResource


class _OwnListReferencesResource(BaseResource):
    """The filter values of one of the user's lists: what occurs in that list.

    Unlike ``client.catalog.references``, each list only has the genres, types, years and age
    ratings of the releases the user put in it; for an empty list they are empty.

    Attributes:
        _REFERENCES_PATH: Path prefix of the list's reference endpoints.
    """

    _REFERENCES_PATH: ClassVar[str]

    async def genres(self) -> list[Genre]:
        """Get the genres of the releases in the list.

        Returns:
            Genres with ``id`` and ``name`` only.

        Raises:
            AuthRequiredError: No valid session.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Genre``.

        Example:
            ```python
            # The same for client.me.collections.references.
            genres = await client.me.favorites.references.genres()
            print([genre.name for genre in genres])
            ```
        """
        return await self._get(f"{self._REFERENCES_PATH}/genres", list[Genre])

    async def types(self) -> list[ValueDescription[str]]:
        """Get the release types in the list, e.g. ``value="TV"``, ``description="ТВ"``.

        Returns:
            The release types.

        Raises:
            AuthRequiredError: No valid session.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``ValueDescription``.

        Example:
            ```python
            types = await client.me.favorites.references.types()
            page = await client.me.favorites.releases(types=types)
            ```
        """
        return await self._get(f"{self._REFERENCES_PATH}/types", list[ValueDescription[str]])

    async def years(self) -> list[int]:
        """Get the release years in the list, newest first.

        Returns:
            The years.

        Raises:
            AuthRequiredError: No valid session.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response wasn't a list of integers.

        Example:
            ```python
            years = await client.me.favorites.references.years()
            page = await client.me.favorites.releases(years=years[:1])  # the newest year
            ```
        """
        return await self._get(f"{self._REFERENCES_PATH}/years", list[int])

    async def age_ratings(self) -> list[AgeRating]:
        """Get the age ratings in the list, e.g. ``value="R16_PLUS"``, ``label="16+"``.

        Returns:
            The age ratings (``is_adult`` is ``None`` here).

        Raises:
            AuthRequiredError: No valid session.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``AgeRating``.

        Example:
            ```python
            for rating in await client.me.collections.references.age_ratings():
                print(rating.value, rating.label)
            ```
        """
        return await self._get(f"{self._REFERENCES_PATH}/age-ratings", list[AgeRating])
