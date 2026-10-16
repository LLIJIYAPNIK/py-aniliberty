"""Franchise models (spec tag ``Аниме.Франшизы``)."""

from __future__ import annotations

from pydantic import Field

from aniliberty.models._base import AniLibertyModel
from aniliberty.models.common import Image
from aniliberty.models.release import Release


class FranchiseRelease(AniLibertyModel):
    """One release of a franchise, with its place in the franchise.

    Spec schema: ``models.anime.franchises.v1.franchise.release``.

    Attributes:
        id: ID of this release-to-franchise link (a UUID string).
        franchise_id: ID of the franchise.
        release_id: ID of the release.
        sort_order: Position of the release in the franchise, starting at 1 — in every
            franchise checked, the chronological order.
        release: The release itself (without ``genres`` and ``episodes``; fetch it with
            ``client.releases.get()`` for those).
    """

    id: str
    franchise_id: str
    release_id: int
    sort_order: int
    release: Release


class Franchise(AniLibertyModel):
    """A franchise: a group of related releases (seasons, movies, spin-offs).

    Spec schema: ``models.anime.franchises.v1.franchise``. The totals are precomputed by the
    API and can be missing or stale — two franchises with ``total_releases=None`` still had
    two releases each — so count ``franchise_releases`` when the exact number matters.

    Attributes:
        id: Franchise ID (a UUID string).
        name: Name in Russian.
        name_english: Name in English or romanized.
        image: Franchise cover image (its paths can be ``None``).
        rating: Franchise rating — ``None`` for every franchise at the time of writing.
        first_year: Year of the first release.
        last_year: Year of the latest release.
        total_releases: Number of releases.
        total_episodes: Number of episodes across all releases.
        total_duration: Total watch time as human-readable Russian text, e.g. ``"10 часов"``.
        total_duration_in_seconds: Total watch time, in seconds.
        franchise_releases: The releases, ordered by ``sort_order`` — only filled in by
            ``client.franchises.get()`` and ``client.franchises.for_release()``.

    Example:
        ```python
        franchise = await client.franchises.get(franchise_id)
        for item in franchise.franchise_releases:
            print(item.sort_order, item.release.year, item.release.name.main)
        ```
    """

    id: str
    name: str
    name_english: str | None = None
    image: Image | None = None
    rating: float | None = None
    first_year: int | None = None
    last_year: int | None = None
    total_releases: int | None = None
    total_episodes: int | None = None
    total_duration: str | None = None
    total_duration_in_seconds: int | None = None
    franchise_releases: list[FranchiseRelease] = Field(default_factory=list)
