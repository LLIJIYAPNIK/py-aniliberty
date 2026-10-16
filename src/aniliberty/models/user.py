"""User account models (spec tag ``Аккаунты.Пользователи.Мое.Профиль``)."""

from datetime import datetime

from pydantic import Field

from aniliberty.models._base import AniLibertyModel
from aniliberty.models.common import Image


class TorrentStats(AniLibertyModel):
    """The account's torrent tracker data.

    Spec schema: ``models.users.v1.user`` → ``torrents``.

    Attributes:
        passkey: The account's tracker passkey — the ``pk`` of ``.torrent`` and RSS links,
            also put into ``magnet`` links of torrents when logged in. A secret: it's left out
            of the model's ``repr``.
        uploaded: Total uploaded, in bytes; ``None`` until the account has uploaded anything.
        downloaded: Total downloaded, in bytes; ``None`` until the account has downloaded
            anything.
    """

    passkey: str | None = Field(default=None, repr=False)
    uploaded: int | None = None
    downloaded: int | None = None


class UserProfile(AniLibertyModel):
    """The logged-in user's own profile, returned by ``client.me.profile()``.

    Spec schema: ``models.users.v1.user``. ``email`` and ``torrents.passkey`` are only sent
    for the user's own profile.

    Attributes:
        id: User ID.
        login: Login, used to log in (together with ``email``).
        email: E-mail of the account.
        nickname: Display name; defaults to the login for a new account.
        avatar: Avatar; all paths are ``None`` without one.
        torrents: Tracker passkey and traffic.
        is_banned: Whether the user is banned on the site.
        created_at: When the account was created.
        is_with_ads: Whether ads are shown to the user — in the spec, but not sent by the API
            at the time of writing (see the three flags below).
        is_with_video_ads: Whether video ads are shown (not in the spec).
        is_with_content_ads: Whether ads are shown among the site's content (not in the spec).
        is_with_video_ads_always: An ad flag the API doesn't document (not in the spec); it
            matches the ``isWithVideoAdsAlways`` parameter of the user's HLS links.
    """

    id: int
    login: str
    email: str | None = None
    nickname: str | None = None
    avatar: Image | None = None
    torrents: TorrentStats | None = None
    is_banned: bool | None = None
    created_at: datetime | None = None
    is_with_ads: bool | None = None
    is_with_video_ads: bool | None = None
    is_with_content_ads: bool | None = None
    is_with_video_ads_always: bool | None = None
