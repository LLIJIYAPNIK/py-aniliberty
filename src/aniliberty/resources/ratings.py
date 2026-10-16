"""``client.releases.ratings`` — the ``Аниме.Релизы.Оценки`` tag of the spec."""

from __future__ import annotations

from aniliberty.models.release import Release, UserRating
from aniliberty.resources._base import BaseResource
from aniliberty.resources._filters import numeric_release_id


class RatingsResource(BaseResource):
    """The logged-in user's own scores of releases, available as ``client.releases.ratings``.

    Needs a session (``client.auth.login()`` or ``AniLiberty(token=...)``); without a valid
    one every method raises ``AuthRequiredError``. Releases are identified by numeric ID only:
    the API answers an alias with a 404, so a ``str`` is rejected.

    The release's overall ``Release.rating`` is computed by the API on its own schedule: it
    didn't change within several minutes of a score being set (see ``docs/api-notes.md``).
    """

    ENDPOINTS = (
        ("GET", "/anime/releases/{releaseId}/rating"),
        ("POST", "/anime/releases/{releaseId}/rating"),
        ("DELETE", "/anime/releases/{releaseId}/rating"),
    )

    async def get(self, release: int | Release) -> UserRating:
        """Get the user's score for a release.

        Args:
            release: Release ID, or a ``Release``.

        Returns:
            The score; ``score`` is ``None`` if the user hasn't rated the release.

        Raises:
            TypeError: ``release`` is not an ``int`` or a ``Release``.
            AuthRequiredError: No valid session.
            NotFoundError: No release with this ID.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``UserRating``.

        Example:
            ```python
            mine = await client.releases.ratings.get(9839)
            print(mine.score)  # e.g. 8, or None
            ```
        """
        return await self._get(_path(release), UserRating)

    async def set(self, release: int | Release, *, score: int) -> UserRating:
        """Rate a release, or change the user's score for it.

        Args:
            release: Release ID, or a ``Release``.
            score: Whole number from 1 to 10.

        Returns:
            The saved score.

        Raises:
            TypeError: ``release`` is not an ``int`` or a ``Release``, or ``score`` isn't an
                ``int``.
            ValueError: ``score`` is outside 1..10.
            AuthRequiredError: No valid session.
            NotFoundError: No release with this ID.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``UserRating``.

        Example:
            ```python
            await client.releases.ratings.set(release, score=9)
            ```
        """
        if isinstance(score, bool) or not isinstance(score, int):
            raise TypeError(f"score must be an int from 1 to 10, got {score!r}")
        if not 1 <= score <= 10:
            raise ValueError(f"score must be from 1 to 10, got {score}")
        path = _path(release)
        payload = await self._http.request("POST", path, json={"score": score})
        return self._parse(payload, UserRating, path=path)

    async def remove(self, release: int | Release) -> UserRating:
        """Withdraw the user's score for a release. A no-op if there is none.

        Args:
            release: Release ID, or a ``Release``.

        Returns:
            The rating afterwards, with ``score`` ``None``.

        Raises:
            TypeError: ``release`` is not an ``int`` or a ``Release``.
            AuthRequiredError: No valid session.
            NotFoundError: No release with this ID.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``UserRating``.

        Example:
            ```python
            await client.releases.ratings.remove(9839)
            ```
        """
        path = _path(release)
        payload = await self._http.request("DELETE", path)
        return self._parse(payload, UserRating, path=path)


def _path(release: int | Release) -> str:
    return f"/anime/releases/{numeric_release_id(release)}/rating"
