"""``client.franchises`` — the ``Аниме.Франшизы`` tag of the spec."""

from __future__ import annotations

import builtins

from aniliberty.models.franchise import Franchise
from aniliberty.models.release import Release
from aniliberty.resources._base import BaseResource, path_segment
from aniliberty.resources._filters import numeric_release_id


class FranchisesResource(BaseResource):
    """Franchises — groups of related releases, available as ``client.franchises``."""

    ENDPOINTS = (
        ("GET", "/anime/franchises"),
        ("GET", "/anime/franchises/{franchiseId}"),
        ("GET", "/anime/franchises/random"),
        ("GET", "/anime/franchises/release/{releaseId}"),
    )

    async def list(self) -> builtins.list[Franchise]:
        """Get all franchises (a few hundred, in one response).

        Returns:
            Every franchise, without ``franchise_releases``.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Franchise``.

        Example:
            ```python
            franchises = await client.franchises.list()
            biggest = max(franchises, key=lambda f: f.total_releases or 0)
            ```
        """
        return await self._get("/anime/franchises", builtins.list[Franchise])

    async def get(self, franchise: str | Franchise) -> Franchise:
        """Get one franchise with its releases.

        Args:
            franchise: Franchise ID (a UUID string), or a ``Franchise`` from ``list()`` /
                ``random()`` to fetch its releases.

        Returns:
            The franchise, with ``franchise_releases`` in order.

        Raises:
            NotFoundError: No franchise with this ID.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Franchise``.

        Example:
            ```python
            franchise = (await client.franchises.list())[0]
            full = await client.franchises.get(franchise)
            print(full.name, [fr.release.name.main for fr in full.franchise_releases])
            ```
        """
        franchise_id = franchise.id if isinstance(franchise, Franchise) else franchise
        if not isinstance(franchise_id, str):
            raise TypeError(f"Expected a franchise ID (str) or a Franchise, got {franchise!r}")
        return await self._get(
            f"/anime/franchises/{path_segment(franchise_id, what='franchise ID')}", Franchise
        )

    async def random(self, *, limit: int | None = None) -> builtins.list[Franchise]:
        """Get random franchises.

        Args:
            limit: How many franchises to return. **Omitted, 0, or more than there are, the
                API returns all franchises** (a few hundred) — pass a limit.

        Returns:
            The franchises, without ``franchise_releases``.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Franchise``.

        Example:
            ```python
            for franchise in await client.franchises.random(limit=3):
                print(franchise.name, franchise.first_year, franchise.last_year)
            ```
        """
        return await self._get(
            "/anime/franchises/random", builtins.list[Franchise], params={"limit": limit}
        )

    async def for_release(self, release: int | Release) -> builtins.list[Franchise]:
        """Get the franchises a release belongs to.

        Args:
            release: Release ID, or a ``Release``. Only numeric IDs work here: the API answers
                an alias with a 404 even for an existing release, so a ``str`` is rejected.

        Returns:
            The franchises (usually one), with ``franchise_releases``; an empty list if the
            release isn't part of any franchise.

        Raises:
            TypeError: ``release`` is not an ``int`` or a ``Release``.
            NotFoundError: No release with this ID.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Franchise``.

        Example:
            ```python
            release = await client.releases.get("sousou-no-frieren")
            for franchise in await client.franchises.for_release(release):
                print(franchise.name, [r.release.name.main for r in franchise.franchise_releases])
            ```
        """
        release_id = numeric_release_id(release)
        return await self._get(f"/anime/franchises/release/{release_id}", builtins.list[Franchise])
