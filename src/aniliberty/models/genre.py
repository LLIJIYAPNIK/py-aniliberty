"""Genre model (spec tag ``Аниме.Жанры``)."""

from __future__ import annotations

from aniliberty.models._base import AniLibertyModel
from aniliberty.models.common import Image


class Genre(AniLibertyModel):
    """An anime genre.

    Spec schema: ``models.anime.genres.v1.genre``.

    Attributes:
        id: Genre ID — the value to pass to catalog genre filters.
        name: Genre name, in Russian (e.g. ``"Экшен"``).
        image: Genre cover image.
        total_releases: Number of releases with this genre.
    """

    id: int
    name: str
    image: Image | None = None
    total_releases: int | None = None
