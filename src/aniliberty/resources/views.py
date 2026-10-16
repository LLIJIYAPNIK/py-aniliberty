"""``client.me.views`` — the ``Аккаунты.Пользователи.Мое.Просмотры`` tag of the spec."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

from aniliberty.models.episode import Episode
from aniliberty.models.view import HistoryEntry, Timecode
from aniliberty.pagination import Page, iterate_pages
from aniliberty.resources._base import BaseResource

_PATH = "/accounts/users/me/views"


class ViewsResource(BaseResource):
    """The user's watch progress and history, available as ``client.me.views``.

    Needs a session (``client.auth.login()`` or ``AniLiberty(token=...)``); without a valid
    one every method raises ``AuthRequiredError``.

    **The API stores timecodes in two steps** (see ``docs/api-notes.md``):

    - ``save_timecodes()`` shows up in ``timecodes()`` at once, but in ``history()``,
      ``client.episodes.timecode()`` and ``client.releases.timecodes()`` only about a minute
      later.
    - ``remove_timecodes()`` likewise takes about a minute to reach the history, and
      ``timecodes()`` can keep listing the deleted entries after that; deleting them once more
      after the minute clears them.

    Example:
        ```python
        await client.me.views.save_timecodes(
            Timecode(release_episode_id=episode.id, time=743.5, is_watched=False)
        )
        progress = {t.release_episode_id: t for t in await client.me.views.timecodes()}
        ```
    """

    ENDPOINTS = (
        ("GET", "/accounts/users/me/views/timecodes"),
        ("POST", "/accounts/users/me/views/timecodes"),
        ("DELETE", "/accounts/users/me/views/timecodes"),
        ("GET", "/accounts/users/me/views/history"),
    )

    async def timecodes(self, *, since: datetime | None = None) -> list[Timecode]:
        """Get the user's timecodes — the position in every episode they started.

        Args:
            since: Only timecodes saved at or after this moment. Must be timezone-aware
                (e.g. ``datetime.now(UTC) - timedelta(days=7)``).

        Returns:
            The timecodes, in no documented order (updating one doesn't move it).

        Raises:
            ValueError: ``since`` has no time zone.
            AuthRequiredError: No valid session.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Timecode``.

        Example:
            ```python
            for timecode in await client.me.views.timecodes():
                print(timecode.release_episode_id, timecode.time, timecode.is_watched)
            ```
        """
        if since is not None and (since.tzinfo is None or since.utcoffset() is None):
            raise ValueError("since must be timezone-aware, e.g. datetime(..., tzinfo=UTC)")
        params = None if since is None else {"since": since.isoformat()}
        return await self._get(f"{_PATH}/timecodes", list[Timecode], params=params)

    async def save_timecodes(self, *timecodes: Timecode) -> None:
        """Save the position in one or more episodes, replacing what was saved for them.

        Args:
            *timecodes: One ``Timecode`` per episode.

        Raises:
            ValueError: No timecodes given.
            TypeError: A value isn't a ``Timecode``.
            AuthRequiredError: No valid session.
            ValidationError: An episode ID isn't a UUID. An ID of an episode that doesn't
                exist is accepted, and dropped later by the API.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.

        Example:
            ```python
            await client.me.views.save_timecodes(
                Timecode(release_episode_id=episode.id, time=episode.duration, is_watched=True)
            )
            ```
        """
        if not timecodes:
            raise ValueError("Pass at least one Timecode")
        for timecode in timecodes:
            if not isinstance(timecode, Timecode):
                raise TypeError(f"Expected a Timecode, got {timecode!r}")
        body = [timecode.model_dump(mode="json") for timecode in timecodes]
        await self._http.request("POST", f"{_PATH}/timecodes", json=body)

    async def remove_timecodes(self, *episodes: str | Episode | Timecode) -> None:
        """Delete the saved position in one or more episodes (and their history entries).

        Episodes without a timecode are skipped. See the class docs: the deletion takes about
        a minute, and ``timecodes()`` may need a second call after that.

        Args:
            *episodes: Episode IDs, or ``Episode``/``Timecode`` objects.

        Raises:
            ValueError: No episodes given.
            TypeError: A value isn't an episode ID, ``Episode`` or ``Timecode``.
            AuthRequiredError: No valid session.
            ValidationError: An episode ID isn't a UUID.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.

        Example:
            ```python
            await client.me.views.remove_timecodes(*await client.me.views.timecodes())
            ```
        """
        if not episodes:
            raise ValueError("Pass at least one episode (an ID, Episode or Timecode)")
        body = [{"release_episode_id": _episode_id(episode)} for episode in episodes]
        await self._http.request("DELETE", f"{_PATH}/timecodes", json=body)

    async def history(
        self, *, page: int | None = None, limit: int | None = None
    ) -> Page[HistoryEntry]:
        """Get one page of the watch history — one entry per episode, most recent first.

        Args:
            page: Page number, starting at 1. A page past the last one is empty.
            limit: Page size, 1 to 50. Default: 25.

        Returns:
            One page of entries, each with its episode and the episode's release.

        Raises:
            AuthRequiredError: No valid session.
            ValidationError: ``page`` or ``limit`` is out of range.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``HistoryEntry``.

        Example:
            ```python
            page = await client.me.views.history(limit=10)
            for entry in page.items:
                episode = entry.release_episode
                print(episode.release.name.main, episode.ordinal, entry.time)
            ```
        """
        return await self._get(
            f"{_PATH}/history", Page[HistoryEntry], params={"page": page, "limit": limit}
        )

    def iter_history(self, *, limit: int | None = None) -> AsyncIterator[HistoryEntry]:
        """Iterate over the whole watch history, fetching page by page.

        Args:
            limit: Page size, 1 to 50 — affects how many requests are made, not the result.

        Returns:
            An async iterator over the entries, most recent first.

        Example:
            ```python
            async for entry in client.me.views.iter_history(limit=50):
                print(entry.updated_at, entry.release_episode_id)
            ```
        """

        async def fetch(page: int) -> Page[HistoryEntry]:
            return await self.history(page=page, limit=limit)

        return iterate_pages(fetch)


def _episode_id(episode: str | Episode | Timecode) -> str:
    if isinstance(episode, Episode):
        return episode.id
    if isinstance(episode, Timecode):
        return episode.release_episode_id
    if isinstance(episode, str) and episode:
        return episode
    raise TypeError(f"Expected an episode ID, Episode or Timecode, got {episode!r}")
