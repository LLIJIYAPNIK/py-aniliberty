"""The airing schedule: what comes out today, and the whole week by weekday.

client.schedule covers ongoing releases only. Each item is a ScheduledRelease: the release
itself plus where it stands this week — whether this week's episode is already out and which
episode is next. The schedule changes every week, so the output below is a snapshot.
"""

import asyncio

from aniliberty import AniLiberty, ScheduledRelease


def describe(item: ScheduledRelease) -> str:
    """One line per release: its title and this week's episode status.

    "This week" is the calendar week starting on Monday. An episode can come out on a
    different day than the release's publish_day, so a release scheduled for a day that
    hasn't come yet can already have this week's episode out.
    """
    episode = item.published_release_episode
    if episode is not None:
        status = f"episode {episode.ordinal} is out"
    elif item.full_season_is_released:
        status = "the whole season is out"
    else:
        status = f"waiting for episode {item.next_release_episode_number}"
    return f"{item.release.name.main} — {status}"


async def main() -> None:
    async with AniLiberty() as client:
        # now() returns three lists: yesterday, today and tomorrow. "Today" follows the
        # API's own calendar; in the checks so far it matched the current UTC weekday.
        schedule = await client.schedule.now()
        print("Today:")
        for item in schedule.today:
            print("  " + describe(item))
            # published_release_episode is a full Episode: its HLS links are right here,
            # no extra request needed.
            episode = item.published_release_episode
            if episode is not None:
                print("    " + str(episode.hls_1080 or episode.hls_720)[:70] + "...")
        print(f"Yesterday: {len(schedule.yesterday)} releases, tomorrow: {len(schedule.tomorrow)}")

        # week() returns every release of the current week in no particular order. Group by
        # release.publish_day: `value` is the weekday number (1 = Monday), `description` its
        # name in Russian.
        week = await client.schedule.week()
        by_day: dict[int, list[ScheduledRelease]] = {}
        names: dict[int, str] = {}
        for item in week:
            day = item.release.publish_day
            if day is None:  # not expected in the schedule, but the field is optional
                continue
            by_day.setdefault(day.value, []).append(item)
            names[day.value] = day.description or str(day.value)

        print(f"This week: {len(week)} releases")
        for day_number in sorted(by_day):
            items = by_day[day_number]
            out = sum(1 for item in items if item.published_release_episode is not None)
            print(f"  {names[day_number]}: {len(items)} releases, {out} already out this week")


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# Today:
#   Небеса у берегов Красной реки — waiting for episode 15
#   Ван-Пис — waiting for episode 21
#   О моём перерождении в меч 2 — episode 3 is out
#     https://cache.libria.fun/videos/media/ts/10297/3/1080/934fbfebe8559bc9...
# Yesterday: 1 releases, tomorrow: 4
# This week: 37 releases
#   Понедельник: 13 releases, 10 already out this week
#   Вторник: 2 releases, 2 already out this week
#   Среда: 7 releases, 7 already out this week
#   Четверг: 1 releases, 1 already out this week
#   Пятница: 3 releases, 1 already out this week
#   Суббота: 4 releases, 1 already out this week
#   Воскресенье: 7 releases, 0 already out this week
