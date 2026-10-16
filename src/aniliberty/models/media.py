"""Media models (spec tags ``Медиа.Промо`` and ``Медиа.Видеоконтент``)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from aniliberty.models._base import AniLibertyModel
from aniliberty.models.common import EMPTY_VALUE_AS_NONE, Image, ValueDescription
from aniliberty.models.release import Release


class Promotion(AniLibertyModel):
    """A promo banner from the site's front page: a featured release, a news post or an ad.

    Spec schema: ``models.media.promotions.v1.promotion``. What a promotion links to
    depends on its kind: a featured release has ``release`` and no ``url``; a news post or
    an ad has ``url`` (and usually ``url_label``) and no ``release``.

    Attributes:
        id: Promotion ID (a UUID string).
        title: Banner title, e.g. the release name — can be ``None``.
        description: Banner text — can be ``None``.
        image: Banner image.
        url: External link the banner points to (absolute), or ``None``.
        url_label: Text for the link button, e.g. ``"Подписаться на канал"``, or ``None``.
        release: The featured release (with ``genres``, without ``episodes``), or ``None``.
        is_ad: Whether this is a paid ad rather than the site's own promo.
        has_overlay: Whether the site darkens the image under the text.
        ad_erid: Ad registry token (ERID) of an ad — ``None`` on every promotion at the time
            of writing.
        ad_origin: Advertiser of an ad — ``None`` on every promotion at the time of writing.

    Example:
        ```python
        for promo in await client.media.promotions():
            if promo.release:
                print("Featured:", promo.release.name.main)
        ```
    """

    id: str
    title: str | None = None
    description: str | None = None
    image: Image | None = None
    url: str | None = None
    url_label: str | None = None
    release: Release | None = None
    is_ad: bool = False
    has_overlay: bool = False
    ad_erid: str | None = None
    ad_origin: str | None = None


class VideoOrigin(AniLibertyModel):
    """Where a video comes from: a YouTube playlist the site tracks.

    Spec schema: ``models.media.videos.v1.video.origin``.

    Attributes:
        id: Origin ID (a UUID string).
        title: Playlist or channel name, e.g. ``"AniLiberty"``.
        description: Playlist description in Russian.
        url: Playlist URL.
        type: Source type. ``type.value`` is ``"YOUTUBE_PLAYLIST"`` — the only value in the
            spec (enum ``enums.media.videos.video.origin.type``) and on every video seen.
        is_announce: Whether the playlist holds season announcements.
    """

    id: str
    title: str | None = None
    description: str | None = None
    url: str | None = None
    type: Annotated[ValueDescription[str] | None, EMPTY_VALUE_AS_NONE] = None
    is_announce: bool = False


class Video(AniLibertyModel):
    """A video from one of AniLibria's YouTube playlists: trailers, reviews, announcements.

    Spec schema: items of ``responses.v1.media.videos`` (``models.media.videos.v1.video.content``
    with ``origin`` added).

    Attributes:
        id: Video ID on the site.
        title: Video title.
        url: Link to watch the video (``https://www.youtube.com/watch?v=...``).
        video_id: The video's YouTube ID.
        image: Preview image (its paths can be ``None``).
        views: View count, as last synced from YouTube — can be ``None``.
        comments: Comment count, as last synced from YouTube — can be ``None``.
        is_announce: Whether the video is a season announcement.
        origin: The playlist the video comes from.
        created_at: When the video was published.
        updated_at: When the site last synced the video's data.
    """

    id: int
    title: str
    url: str
    video_id: str
    image: Image | None = None
    views: int | None = None
    comments: int | None = None
    is_announce: bool = False
    origin: VideoOrigin | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
