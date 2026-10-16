"""Schedule models (spec tag ``Аниме.Релизы.РасписаниеРелизов``)."""

from __future__ import annotations

from pydantic import Field

from aniliberty.models._base import AniLibertyModel
from aniliberty.models.episode import Episode
from aniliberty.models.release import Release


class ScheduledRelease(AniLibertyModel):
    """A release in the airing schedule, with where it stands this week.

    Spec schema: ``models.anime.schedule.v1.releaseInSchedule``. The weekday a release comes
    out on is ``release.publish_day`` (``value`` 1 = Monday ... 7 = Sunday).

    Attributes:
        release: The release, with ``genres`` filled in.
        published_release_episode: The episode that came out during the current week
            (Monday to Sunday), or ``None`` if this week's episode isn't out yet. It can come
            out on a different day than ``publish_day`` — e.g. a Saturday release whose
            episode was out on Tuesday.
        next_release_episode_number: Number of the next episode to come out, ``None`` when
            no further episode is expected.
        full_season_is_released: Whether all episodes of the season are already out.

    Example:
        ```python
        for item in await client.schedule.week():
            day = item.release.publish_day.description if item.release.publish_day else "?"
            print(day, item.release.name.main, item.next_release_episode_number)
        ```
    """

    release: Release
    published_release_episode: Episode | None = None
    next_release_episode_number: int | None = None
    full_season_is_released: bool


class ScheduleNow(AniLibertyModel):
    """Releases scheduled for yesterday, today and tomorrow.

    Spec schema: ``responses.v1.anime.schedule.now``. Each list holds the releases whose
    ``publish_day`` is that day of the week.

    Attributes:
        yesterday: Releases that came out (or were due) yesterday.
        today: Releases due today.
        tomorrow: Releases due tomorrow.
    """

    yesterday: list[ScheduledRelease] = Field(default_factory=list)
    today: list[ScheduledRelease] = Field(default_factory=list)
    tomorrow: list[ScheduledRelease] = Field(default_factory=list)
