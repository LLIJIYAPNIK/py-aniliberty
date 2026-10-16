"""Episode models (spec tag ``Аниме.Релизы.Эпизоды``)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any

from pydantic import BeforeValidator

from aniliberty.models._base import AniLibertyModel
from aniliberty.models.common import Image

if TYPE_CHECKING:
    from aniliberty.models.release import Release


def _empty_skip_as_none(data: Any) -> Any:
    if isinstance(data, dict) and data.get("start") is None and data.get("stop") is None:
        return None
    return data


class SkipRange(AniLibertyModel):
    """Where an opening or ending is, so a player can offer to skip it.

    The spec describes the numbers as "seconds from the start or the end of the episode";
    in every live sample checked they were seconds from the **start** (an ending of a
    1502-second episode at ``1326``–``1502``), see ``docs/api-notes.md``.

    Attributes:
        start: Where the segment starts, in seconds.
        stop: Where the segment ends, in seconds.
    """

    start: int | None = None
    stop: int | None = None


class Episode(AniLibertyModel):
    """An episode of a release, with links to its HLS streams.

    Spec schema: ``models.anime.releases.v1.release.episode``. HLS links are absolute URLs of
    ``.m3u8`` playlists on the video CDN, returned exactly as the API sends them — their query
    string (country, ads flags, ...) is part of the link. Downloading the video itself is out
    of scope for the SDK: hand the playlist to a player or to ``ffmpeg``.

    Attributes:
        id: Episode ID (a UUID string) — pass it to ``client.episodes.get()``.
        release_id: ID of the release the episode belongs to.
        ordinal: Episode number. Usually an ``int``; the spec allows fractions such as
            ``12.5`` for recap/special episodes, which come as a ``float``.
        sort_order: Position of the episode in the release's list.
        name: Episode title, in Russian, if it has one (most don't).
        name_english: Episode title in English, if any.
        duration: Length, in seconds.
        opening: Where the opening is, ``None`` if not marked.
        ending: Where the ending is, ``None`` if not marked.
        preview: Still image from the episode. Often present with all paths ``None``.
        hls_480: HLS playlist, 480p.
        hls_720: HLS playlist, 720p.
        hls_1080: HLS playlist, 1080p — missing on some episodes.
        rutube_id: ID of the episode on Rutube, if it's published there.
        youtube_id: ID of the episode on YouTube, if it's published there.
        updated_at: When the episode was last updated.
        release: The release with all its episodes — only filled in by
            ``client.episodes.get()``.

    Example:
        ```python
        episode = await client.episodes.get(release.episodes[0].id)
        playlist = episode.hls_1080 or episode.hls_720 or episode.hls_480
        ```
    """

    id: str
    release_id: int
    ordinal: int | float
    sort_order: int
    name: str | None = None
    name_english: str | None = None
    duration: int
    opening: Annotated[SkipRange | None, BeforeValidator(_empty_skip_as_none)] = None
    ending: Annotated[SkipRange | None, BeforeValidator(_empty_skip_as_none)] = None
    preview: Image | None = None
    hls_480: str | None = None
    hls_720: str | None = None
    hls_1080: str | None = None
    rutube_id: str | None = None
    youtube_id: str | None = None
    updated_at: datetime | None = None
    release: Release | None = None
