"""``client.app`` — the ``Приложение.*`` tags of the spec."""

from __future__ import annotations

from aniliberty.models.app import ApiStatus
from aniliberty.models.release import Release
from aniliberty.resources._base import BaseResource


class AppResource(BaseResource):
    """Service endpoints of the API, available as ``client.app``."""

    ENDPOINTS = (("GET", "/app/status"), ("GET", "/app/search/releases"))

    async def status(self) -> ApiStatus:
        """Get the status of the API.

        A cheap request that is handy as a health check. The response also lists the hosts
        the API is available at, which can be used as ``base_url`` mirrors.

        Returns:
            The API status.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``ApiStatus``.

        Example:
            ```python
            async with AniLiberty() as client:
                status = await client.app.status()
                print(status.is_alive, status.available_api_endpoints)
            ```
        """
        return await self._get("/app/status", ApiStatus)

    async def search_releases(self, query: str, *, refresh: bool = False) -> list[Release]:
        """Quick search of releases by name — the search box of the site.

        Matches Russian and English names and aliases, fuzzily: ``"frieren"``,
        ``"Фрирен"`` and ``"sousou-no-frieren"`` find the same release. There is no paging
        and no ``limit``: the API returns a short list (at most 20 releases in every query
        checked), in an order it chooses. For filtered, paginated search use the catalog
        instead.

        Args:
            query: Search text.
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            Matching releases, without the per-endpoint extras (``genres`` etc. are empty);
            an empty list when nothing matches.

        Raises:
            ValidationError: ``query`` is empty.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Release``.

        Example:
            ```python
            for release in await client.app.search_releases("frieren"):
                print(release.id, release.name.main)
            ```
        """
        return await self._get(
            "/app/search/releases",
            list[Release],
            params={"query": query},
            cache=True,
            refresh=refresh,
        )
