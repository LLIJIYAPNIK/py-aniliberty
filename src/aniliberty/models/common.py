"""Building blocks shared by many models: value + description pairs and images."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BeforeValidator, PrivateAttr

from aniliberty._http import DEFAULT_SITE_URL
from aniliberty.models._base import AniLibertyModel

T = TypeVar("T")


class ValueDescription(AniLibertyModel, Generic[T]):
    """A machine value with its human-readable (Russian) description.

    The API returns many enumerations this way — a release's type, season, publish day, a
    torrent's quality, ... — e.g. ``{"value": "TV", "description": "ТВ"}`` or
    ``{"value": 5, "description": "Пятница"}`` (``publish_day`` uses weekday numbers). Fields
    with extra keys next to these two (``age_rating``'s ``label``/``is_adult``, a torrent
    codec's ``label_*``) use subclasses.

    Attributes:
        value: The machine value — use it for comparisons and catalog filters.
        description: The value's description in Russian, for display.

    Example:
        ```python
        if release.type and release.type.value == "MOVIE":
            print(release.type.description)  # "Фильм"
        ```
    """

    value: T
    description: str | None = None


def _empty_value_as_none(data: Any) -> Any:
    if isinstance(data, dict) and data.get("value") is None:
        return None
    return data


EMPTY_VALUE_AS_NONE = BeforeValidator(_empty_value_as_none)
"""Turns ``{"value": null, ...}`` into ``None`` for an optional ``ValueDescription`` field.

The API sometimes sends a value + description object with both keys ``null`` — seen on
``season`` of releases in the schedule — instead of omitting it. Annotate such fields as::

    season: Annotated[ValueDescription[str] | None, EMPTY_VALUE_AS_NONE] = None
"""


class ImageSet(AniLibertyModel):
    """Links to one image in several sizes.

    The API sends **relative** paths such as ``/storage/releases/posters/1/abc.jpg``; they
    resolve against the site's origin, not the ``/api/v1`` base URL (see
    ``docs/api-notes.md``). The raw paths are kept in ``src``/``preview``/``thumbnail``, and
    the ``*_url`` properties return absolute URLs on the host the client talked to (or on
    ``https://aniliberty.top`` for a model built by hand).

    Any of the paths can be ``None`` — e.g. a user without an avatar gets an image object
    whose paths are all ``None``.

    Attributes:
        src: Original image path. Only posters and episode previews have it.
        preview: Path of the medium-size image.
        thumbnail: Path of the small image.
    """

    src: str | None = None
    preview: str | None = None
    thumbnail: str | None = None

    _site_url: str = PrivateAttr(default=DEFAULT_SITE_URL)

    def model_post_init(self, context: Any, /) -> None:
        # Resources validate responses with context={"site_url": ...} (the origin of the
        # client's base_url), so images from a mirror point to that mirror.
        if isinstance(context, dict) and isinstance(context.get("site_url"), str):
            self._site_url = context["site_url"]

    @property
    def src_url(self) -> str | None:
        """Absolute URL of ``src``."""
        return self._absolute(self.src)

    @property
    def preview_url(self) -> str | None:
        """Absolute URL of ``preview``."""
        return self._absolute(self.preview)

    @property
    def thumbnail_url(self) -> str | None:
        """Absolute URL of ``thumbnail``."""
        return self._absolute(self.thumbnail)

    def _absolute(self, path: str | None) -> str | None:
        if not path:
            return None
        if path.startswith(("http://", "https://")):
            return path
        if path.startswith("//"):
            return f"https:{path}"
        return f"{self._site_url}/{path.lstrip('/')}"


class Image(ImageSet):
    """An image in its original format plus ``optimized`` (WebP) variants.

    Spec schema: ``commons.v1.models.components.image.withOptimized`` — used for release
    posters, episode previews, genre and franchise images, user avatars.

    Attributes:
        optimized: The same image in WebP, usually smaller.

    Example:
        ```python
        poster = release.poster
        print(poster.preview_url)            # https://aniliberty.top/storage/....jpg
        print(poster.optimized.preview_url)  # https://aniliberty.top/storage/....webp
        ```
    """

    optimized: ImageSet | None = None


class LinkedAccount(AniLibertyModel):
    """The site account linked to a person in the credits or in a team.

    The ``user`` of ``ReleaseMember``, ``TorrentMember`` and ``TeamMember`` — set when the
    person has an account on the site, ``None`` otherwise. Spec schemas:
    ``models.teams.v1.team.user.account`` and the ``user`` of release/torrent members.

    Attributes:
        id: User ID on the site.
        nickname: The account's nickname. Only team members' accounts have it (it can differ
            from the team nickname); for release and torrent members it's ``None`` — their
            own ``nickname`` is on the member.
        avatar: The account's avatar (its paths can be ``None``).
    """

    id: int
    nickname: str | None = None
    avatar: Image | None = None
