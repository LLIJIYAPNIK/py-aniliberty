"""``client.media`` — the ``Медиа.Промо`` and ``Медиа.Видеоконтент`` tags of the spec."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from aniliberty._query import build_query
from aniliberty.models.media import Promotion, Video
from aniliberty.resources._base import BaseResource

T = TypeVar("T")


class MediaResource(BaseResource):
    """Front-page promo banners and AniLibria's YouTube videos, available as ``client.media``.

    The ads endpoints that live under ``/media`` as well (``/media/vasts``,
    ``/media/manifest.xml``, spec tag ``Реклама.Vasts``) are deliberately not covered.
    """

    ENDPOINTS = (
        ("GET", "/media/promotions"),
        ("GET", "/media/videos"),
    )

    async def promotions(self) -> list[Promotion]:
        """Get the promo banners shown on the site's front page.

        Returns:
            Every current promotion (a handful), **in random order** — a new order on each
            call. Paid ads are included; filter them out with ``promo.is_ad``.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Promotion``.

        Example:
            ```python
            promos = [p for p in await client.media.promotions() if not p.is_ad]
            ```
        """
        return await self._get_list("/media/promotions", list[Promotion])

    async def videos(self, *, limit: int | None = None, refresh: bool = False) -> list[Video]:
        """Get the latest videos from AniLibria's YouTube playlists, newest first.

        Args:
            limit: How many videos to return, 1 to 50. Omitted, the API returns 10.
                **0 or a negative number returns all videos** (over a thousand, more than
                1 MB of JSON); more than 50 is a ``ValidationError``.
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            The videos, ordered by ``created_at`` from newest.

        Raises:
            ValidationError: ``limit`` is over 50.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Video``.

        Example:
            ```python
            for video in await client.media.videos(limit=5):
                print(video.created_at.date() if video.created_at else "?", video.title)
            ```
        """
        return await self._get_list(
            "/media/videos", list[Video], params={"limit": limit}, cache=True, refresh=refresh
        )

    async def _get_list(
        self,
        path: str,
        type_: type[T],
        *,
        params: Mapping[str, Any] | None = None,
        cache: bool = False,
        refresh: bool = False,
    ) -> T:
        # The spec documents {"data": [...]}, but the live API returns the list itself (see
        # docs/api-notes.md). Accept both, like client.schedule.week().
        query = build_query(params) if params else None
        payload = await self._http.request("GET", path, params=query, cache=cache, refresh=refresh)
        if isinstance(payload, dict) and "data" in payload:
            payload = payload["data"]
        return self._parse(payload, type_, path=path)
