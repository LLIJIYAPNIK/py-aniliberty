"""``client.schedule`` — the ``Аниме.Релизы.РасписаниеРелизов`` tag of the spec."""

from __future__ import annotations

from aniliberty.models.schedule import ScheduledRelease, ScheduleNow
from aniliberty.resources._base import BaseResource


class ScheduleResource(BaseResource):
    """The weekly airing schedule of ongoing releases, available as ``client.schedule``."""

    ENDPOINTS = (
        ("GET", "/anime/schedule/now"),
        ("GET", "/anime/schedule/week"),
    )

    async def now(self, *, refresh: bool = False) -> ScheduleNow:
        """Get the releases scheduled for yesterday, today and tomorrow.

        Args:
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            The schedule for the three days. Each item says whether this week's episode is
            already out (``published_release_episode``) and which one comes next.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``ScheduleNow``.

        Example:
            ```python
            schedule = await client.schedule.now()
            for item in schedule.today:
                episode = item.published_release_episode
                status = f"episode {episode.ordinal} is out" if episode else "not out yet"
                print(item.release.name.main, "—", status)
            ```
        """
        return await self._get("/anime/schedule/now", ScheduleNow, cache=True, refresh=refresh)

    async def week(self, *, refresh: bool = False) -> list[ScheduledRelease]:
        """Get the schedule for the whole current week.

        The list is not ordered by weekday; group or sort it by
        ``item.release.publish_day.value`` (1 = Monday ... 7 = Sunday) as needed.

        Args:
            refresh: Fetch from the API even if the response is cached (see
                ``AniLiberty(cache_dir=...)``); the new response replaces the cached one.

        Returns:
            All releases in this week's schedule.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``ScheduledRelease``.

        Example:
            ```python
            by_day: dict[int, list[ScheduledRelease]] = {}
            for item in await client.schedule.week():
                day = item.release.publish_day.value if item.release.publish_day else 0
                by_day.setdefault(day, []).append(item)
            ```
        """
        path = "/anime/schedule/week"
        payload = await self._http.request("GET", path, cache=True, refresh=refresh)
        # The spec documents {"data": [...]}, but the live API returns the list itself (see
        # docs/api-notes.md, "Schedule"). Accept both, in case the API is aligned later.
        if isinstance(payload, dict) and "data" in payload:
            payload = payload["data"]
        return self._parse(payload, list[ScheduledRelease], path=path)
