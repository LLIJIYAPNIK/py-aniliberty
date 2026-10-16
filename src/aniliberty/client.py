"""``AniLiberty`` — the SDK's entry point."""

from __future__ import annotations

from collections.abc import Mapping
from types import TracebackType
from typing import Self

import httpx

from aniliberty._http import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_TIMEOUT,
    HttpClient,
)
from aniliberty.resources.app import AppResource
from aniliberty.resources.auth import AuthResource
from aniliberty.resources.catalog import CatalogResource
from aniliberty.resources.episodes import EpisodesResource
from aniliberty.resources.franchises import FranchisesResource
from aniliberty.resources.genres import GenresResource
from aniliberty.resources.me import MeResource
from aniliberty.resources.media import MediaResource
from aniliberty.resources.releases import ReleasesResource
from aniliberty.resources.schedule import ScheduleResource
from aniliberty.resources.teams import TeamsResource
from aniliberty.resources.torrents import TorrentsResource


class AniLiberty:
    """Async client for the AniLibria API.

    Groups the API into resource namespaces that follow the tags of its OpenAPI spec
    (``client.app``, ...). Use it as an async context manager so the connection pool is
    closed when you're done, or call ``aclose()`` yourself.

    Attributes:
        http: The low-level client every resource uses. ``client.http.request(...)`` is the
            escape hatch for endpoints the SDK doesn't cover yet — it returns raw JSON.
        app: Service endpoints — API status and quick release search.
        releases: Anime releases — latest, random, recommended, by ID/alias, members.
        episodes: Episodes of releases, with HLS links.
        catalog: The release catalog; ``catalog.references`` lists the values its filters
            accept.
        schedule: The weekly airing schedule.
        genres: Genres, and the releases of each.
        franchises: Franchises — groups of related releases.
        torrents: Torrents, ``.torrent`` file downloads and RSS feeds.
        teams: AniLibria's own teams, roles and members.
        media: Front-page promo banners and AniLibria's YouTube videos.
        auth: Logging in and out — by password, one-time code or social network.
        me: The logged-in user's own account — profile, favorites, collections
            (needs a session).

    Example:
        ```python
        import asyncio

        from aniliberty import AniLiberty


        async def main() -> None:
            async with AniLiberty() as client:
                status = await client.app.status()
                print(status.is_alive)


        asyncio.run(main())
        ```
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
        headers: Mapping[str, str] | None = None,
        http_client: httpx.AsyncClient | None = None,
        token: str | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: API base URL including the version prefix. Defaults to the main server,
                ``https://aniliberty.top/api/v1``; ``https://anilibria.top/api/v1`` is a
                mirror.
            timeout: Per-request timeout, in seconds. Ignored when ``http_client`` is given.
            max_concurrency: Maximum number of requests in flight at once, no matter how many
                coroutines share this client. Requests over the limit wait for a free slot.
                Consecutive requests are also spaced at least 0.1 s apart, and 429/5xx/network
                failures are retried with backoff — see ``HttpClient``.
            headers: Extra headers sent with every request, merged over the SDK's defaults
                (``Accept: application/json`` and the SDK's ``User-Agent``).
            http_client: A ready ``httpx.AsyncClient`` to send requests with, e.g. to set up
                a proxy. The SDK doesn't close a client it didn't create.
            token: Session token of an earlier login (``client.token`` saved from it), for
                the account endpoints. Without one, call ``client.auth.login()``. Public
                endpoints don't need it.
        """
        self.http = HttpClient(
            base_url=base_url,
            timeout=timeout,
            headers=headers,
            http_client=http_client,
            token=token,
            max_concurrency=max_concurrency,
        )
        self.app = AppResource(self.http)
        self.releases = ReleasesResource(self.http)
        self.episodes = EpisodesResource(self.http)
        self.catalog = CatalogResource(self.http)
        self.schedule = ScheduleResource(self.http)
        self.genres = GenresResource(self.http)
        self.franchises = FranchisesResource(self.http)
        self.torrents = TorrentsResource(self.http)
        self.teams = TeamsResource(self.http)
        self.media = MediaResource(self.http)
        self.auth = AuthResource(self.http)
        self.me = MeResource(self.http)

    @property
    def token(self) -> str | None:
        """The session token sent with every request, or ``None`` when not logged in.

        Set by ``client.auth.login()`` (and the other login methods), cleared by
        ``client.auth.logout()``. Save it to reuse the session later as
        ``AniLiberty(token=...)``; assign ``None`` to stop sending it without ending the
        session. It is a secret — don't log it.
        """
        return self.http.token

    @token.setter
    def token(self, value: str | None) -> None:
        self.http.token = value

    async def __aenter__(self) -> Self:
        if self.http.closed:
            raise RuntimeError(
                "This AniLiberty client has been closed and can't be reused; create a new one."
            )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the connection pool. Safe to call more than once."""
        await self.http.aclose()
