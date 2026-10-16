"""``client.app`` — the ``Приложение.*`` tags of the spec."""

from __future__ import annotations

from aniliberty.models.app import ApiStatus
from aniliberty.resources._base import BaseResource


class AppResource(BaseResource):
    """Service endpoints of the API, available as ``client.app``."""

    ENDPOINTS = (("GET", "/app/status"),)

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
