"""client.schedule against recorded live responses."""

from __future__ import annotations

import pytest

from aniliberty import AniLiberty, ScheduledRelease, ScheduleNow


def weekday(item: ScheduledRelease) -> int | None:
    return item.release.publish_day.value if item.release.publish_day else None


@pytest.mark.vcr
async def test_now_groups_releases_by_consecutive_days() -> None:
    async with AniLiberty() as client:
        schedule = await client.schedule.now()

    assert isinstance(schedule, ScheduleNow)
    days = {}
    for name in ("yesterday", "today", "tomorrow"):
        items = getattr(schedule, name)
        assert items, f"{name} is empty in the recording"
        # Every release in one list comes out on the same weekday.
        [days[name]] = {weekday(item) for item in items}
    assert (days["yesterday"] % 7) + 1 == days["today"]
    assert (days["today"] % 7) + 1 == days["tomorrow"]


@pytest.mark.vcr
async def test_week_contains_the_releases_of_now() -> None:
    async with AniLiberty() as client:
        now = await client.schedule.now()
        week = await client.schedule.week()

    assert all(isinstance(item, ScheduledRelease) for item in week)
    week_ids = {item.release.id for item in week}
    now_ids = {item.release.id for day in (now.yesterday, now.today, now.tomorrow) for item in day}
    assert now_ids <= week_ids
    assert all(item.release.genres for item in week)
    # Some of this week's episodes are out, some aren't yet.
    assert any(item.published_release_episode for item in week)
    assert any(item.published_release_episode is None for item in week)
    for item in week:
        episode = item.published_release_episode
        if episode is not None:
            assert episode.release_id == item.release.id
