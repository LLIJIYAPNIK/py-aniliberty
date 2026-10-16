"""Watch progress models (spec tag ``Аккаунты.Пользователи.Мое.Просмотры`` and the timecode
endpoints of ``Аниме.Релизы``/``Аниме.Релизы.Эпизоды``)."""

from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from aniliberty.models._base import AniLibertyModel
from aniliberty.models.episode import Episode


class Timecode(AniLibertyModel):
    """Where the user stopped in an episode, and whether they finished it.

    What ``client.me.views.save_timecodes()`` takes and ``client.me.views.timecodes()``
    returns. Spec schema: ``responses.v1.accounts.users.me.views.timecodes.item`` — the API
    sends an ``[episode_id, time, is_watched]`` triple, which is validated into this model (a
    dict with the field names works too).

    Attributes:
        release_episode_id: Episode ID (a UUID string), as in ``Episode.id``.
        time: Position in the episode, in seconds from its start (fractions allowed, not
            negative).
        is_watched: Whether the episode counts as watched.

    Example:
        ```python
        Timecode(release_episode_id=episode.id, time=743.5, is_watched=False)
        ```
    """

    release_episode_id: str
    time: float = Field(ge=0)
    is_watched: bool = False

    @model_validator(mode="before")
    @classmethod
    def _from_triple(cls, data: Any) -> Any:
        if isinstance(data, list | tuple) and len(data) == 3:
            return {"release_episode_id": data[0], "time": data[1], "is_watched": data[2]}
        return data


class EpisodeView(AniLibertyModel):
    """The stored watch record of one episode.

    Returned by ``client.episodes.timecode()`` and ``client.releases.timecodes()``. Spec
    schema: ``models.accounts.users.v1.user.view``. Records are written by the API about a
    minute after ``client.me.views.save_timecodes()`` (see ``docs/api-notes.md``).

    Attributes:
        id: Record ID.
        release_episode_id: Episode ID (a UUID string).
        time: Position in the episode, in seconds from its start.
        is_watched: Whether the episode counts as watched.
        updated_at: When the record was last saved.
        user_id: The user the record belongs to.
    """

    id: int
    release_episode_id: str
    time: float
    is_watched: bool
    updated_at: datetime | None = None
    user_id: int | None = None


class HistoryEntry(EpisodeView):
    """An entry of the watch history, from ``client.me.views.history()``.

    Spec schema: ``responses.v1.accounts.users.me.views.history`` → ``data[]``.

    Attributes:
        release_episode: The episode, with its release in ``release_episode.release``.
    """

    release_episode: Episode | None = None
