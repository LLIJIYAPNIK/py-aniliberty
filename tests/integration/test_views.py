"""client.me.views and the timecode endpoints against recorded live responses.

Saved timecodes reach the history (and the per-episode/per-release endpoints) about a minute
later, deletions likewise — see docs/api-notes.md, "Timecodes and watch history". The
scenario polls with ``live_wait`` in between, which only sleeps while recording.

Episodes used (as of 2026-10-16): the first two of release 9839 and the first of 8030. The
scenario starts and ends without timecodes.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import pytest
from conftest import Credentials

from aniliberty import AniLiberty, AuthRequiredError, HistoryEntry, NotFoundError, Timecode

Wait = Callable[[float], Awaitable[None]]
POLLS = 20
POLL_INTERVAL = 10.0


async def until(check: Callable[[], Awaitable[bool]], live_wait: Wait) -> None:
    for _ in range(POLLS):
        if await check():
            return
        await live_wait(POLL_INTERVAL)
    raise AssertionError("the API didn't settle in time")


@pytest.mark.vcr
async def test_timecodes_lifecycle(credentials: Credentials, live_wait: Wait) -> None:
    async with AniLiberty() as client:
        await client.auth.login(login=credentials.login, password=credentials.password)
        views = client.me.views

        async def history_total() -> int:
            return (await views.history()).total

        try:
            assert await views.timecodes() == []
            assert await history_total() == 0

            e1 = (await client.releases.get(9839)).episodes[0]
            e3 = (await client.releases.get(8030)).episodes[0].id

            await views.save_timecodes(
                Timecode(release_episode_id=e1.id, time=743.5),
                Timecode(release_episode_id=e3, time=1400, is_watched=True),
            )
            # The quick list has them at once ...
            assert {
                (t.release_episode_id, t.time, t.is_watched) for t in await views.timecodes()
            } == {
                (e1.id, 743.5, False),
                (e3, 1400.0, True),
            }
            # ... the stored records come about a minute later.
            await until(lambda: _equals(history_total(), 2), live_wait)

            view = await client.episodes.timecode(e1.id)
            assert (view.release_episode_id, view.time, view.is_watched) == (e1.id, 743.5, False)
            assert view.updated_at is not None
            assert [v.release_episode_id for v in await client.releases.timecodes(9839)] == [e1.id]

            history = await views.history()
            assert all(isinstance(entry, HistoryEntry) for entry in history.items)
            releases = {
                entry.release_episode.release.id
                for entry in history.items
                if entry.release_episode and entry.release_episode.release
            }
            assert releases == {9839, 8030}
            assert [e.id async for e in views.iter_history(limit=1)] == [
                e.id for e in history.items
            ]

            future = datetime(2030, 1, 1, tzinfo=UTC)
            assert await views.timecodes(since=future) == []

            await views.remove_timecodes(e1, e3)
            await until(lambda: _equals(history_total(), 0), live_wait)
            with pytest.raises(NotFoundError):
                await client.episodes.timecode(e1.id)
        finally:
            await _clear_timecodes(client, live_wait)
            await client.auth.logout()


async def _equals(value: Awaitable[int], expected: int) -> bool:
    return await value == expected


async def _clear_timecodes(client: AniLiberty, live_wait: Wait) -> None:
    """Delete every timecode until the quick list is empty too (it lags behind deletions)."""
    views = client.me.views
    for _ in range(POLLS):
        left = await views.timecodes()
        if not left:
            return
        await views.remove_timecodes(*left)
        await live_wait(POLL_INTERVAL)
    raise AssertionError("timecodes weren't cleared")


@pytest.mark.vcr
async def test_views_without_session_raise_auth_required() -> None:
    async with AniLiberty() as client:
        with pytest.raises(AuthRequiredError):
            await client.me.views.timecodes()
        with pytest.raises(AuthRequiredError):
            await client.releases.timecodes(9839)
