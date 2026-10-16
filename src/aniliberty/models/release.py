"""Release models (spec tag ``Аниме.Релизы``).

Which fields are required follows ``docs/api-notes.md``, "Optional and nullable fields": the
spec marks nothing as required and too little as nullable, so a field is required only if it
identifies the release or was non-null in every live response checked (2026-10-16, 40+
releases from ``latest``/``random``/``recommended``/``list`` and the release page).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from aniliberty.models._base import AniLibertyModel
from aniliberty.models.common import EMPTY_VALUE_AS_NONE, Image, ImageSet, ValueDescription
from aniliberty.models.episode import Episode
from aniliberty.models.genre import Genre


class ReleaseName(AniLibertyModel):
    """Names of a release.

    Attributes:
        main: The main (Russian) title.
        english: The English or romanized title.
        alternative: Other titles, comma-separated, if any.
    """

    main: str
    english: str | None = None
    alternative: str | None = None


class AgeRating(ValueDescription[str]):
    """Age rating of a release, e.g. ``value="R16_PLUS"``, ``label="16+"``.

    ``value`` is one of ``R0_PLUS``, ``R6_PLUS``, ``R12_PLUS``, ``R16_PLUS``, ``R18_PLUS``
    (spec enum ``enums.anime.releases.release.ageRating``).

    Attributes:
        label: Short label, e.g. ``"16+"``.
        is_adult: Whether the release is for adults only.
    """

    label: str | None = None
    is_adult: bool | None = None


class ExternalRating(AniLibertyModel):
    """A release's entry and score on an external site (Shikimori or MyAnimeList).

    All fields are ``None`` when the release isn't linked to that site.

    Attributes:
        id: ID of the anime on the external site.
        url: Link to the anime's page there.
        rating: Average score there, from 1 to 10.
        votes: Number of people who rated it there.
    """

    id: int | None = None
    url: str | None = None
    rating: float | None = None
    votes: int | None = None


class ReleaseRating(AniLibertyModel):
    """Score given to a release by AniLibria users.

    Attributes:
        average: Average score from 1 to 10, ``None`` if nobody rated it yet.
        votes: Number of people who rated it.
        distribution: Number of votes per score, for every score from 1 to 10.
    """

    average: float | None = None
    votes: int
    distribution: dict[int, int] = Field(default_factory=dict)


class ReleaseMemberUser(AniLibertyModel):
    """The site account linked to a release member.

    Attributes:
        id: User ID.
        avatar: User avatar.
    """

    id: int
    avatar: Image | None = None


class ReleaseMember(AniLibertyModel):
    """A person who worked on a release (voice actor, translator, timer, ...).

    Spec schema: ``models.anime.releases.v1.release.member``.

    Attributes:
        id: Member entry ID (a UUID string).
        nickname: The member's nickname.
        role: What they did. ``role.value`` is one of ``poster``, ``timing``, ``voicing``,
            ``editing``, ``decorating``, ``translating``, ``hevc`` (spec enum
            ``enums.anime.releases.release.member.role``).
        user: Linked site account, if any (usually ``None``).
    """

    id: str
    nickname: str
    role: Annotated[ValueDescription[str] | None, EMPTY_VALUE_AS_NONE] = None
    user: ReleaseMemberUser | None = None


class Sponsor(AniLibertyModel):
    """A sponsor shown on a release page.

    Spec schema: ``models.anime.sponsors.v1.sponsor``.

    Attributes:
        id: Sponsor ID.
        title: Sponsor name.
        description: Sponsor description.
        url: Sponsor link.
        url_title: Text of the sponsor link.
    """

    id: str
    title: str | None = None
    description: str | None = None
    url: str | None = None
    url_title: str | None = None


class Release(AniLibertyModel):
    """An anime release.

    Spec schema: ``models.anime.releases.v1.release`` plus the extra fields each endpoint adds.
    List endpoints fill only part of the extras: ``genres`` comes with every endpoint except
    ``Episode.release``, ``background_covers`` with ``random()`` and ``get()``,
    ``members``/``sponsors`` with ``get()`` and ``list()``, ``episodes`` with ``get()``,
    ``list()`` and ``Episode.release``, ``latest_episode`` with ``latest()`` only. An extra
    the endpoint doesn't send is an empty list or ``None``.

    Attributes:
        id: Release ID.
        alias: URL slug, e.g. ``"tensei-shitara-ken-deshita-2nd-season"``; ``get()`` accepts
            it as well as the ID.
        name: Release names.
        type: Release type; ``type.value`` is one of ``TV``, ``ONA``, ``WEB``, ``OVA``,
            ``OAD``, ``MOVIE``, ``DORAMA``, ``SPECIAL`` (spec enum
            ``enums.anime.releases.release.type``).
        year: Release year.
        season: Release season; ``season.value`` is one of ``winter``, ``spring``,
            ``summer``, ``autumn``.
        poster: Release poster.
        description: Synopsis, in Russian.
        notification: Important notice shown on the release page, if any.
        age_rating: Age rating.
        publish_day: Weekday new episodes come out on; ``publish_day.value`` is 1 (Monday)
            to 7 (Sunday).
        is_ongoing: Whether the anime is still airing in its home country.
        is_in_production: Whether AniLibria is still dubbing it.
        is_blocked_by_geo: Whether it's blocked in the requester's region.
        is_blocked_by_copyrights: Whether it's blocked by the copyright holder.
        episodes_total: Number of episodes, if known.
        average_duration_of_episode: Average episode length, in minutes, if known.
        external_player: Link to an external player, if any.
        fresh_at: When the release was last bumped (e.g. by a new episode).
        created_at: When the release was added.
        updated_at: When the release was last edited.
        added_in_users_favorites: How many users added it to favorites.
        added_in_planned_collection: How many users put it in their "planned" collection.
        added_in_watched_collection: How many users put it in "watched".
        added_in_watching_collection: How many users put it in "watching".
        added_in_postponed_collection: How many users put it in "postponed".
        added_in_abandoned_collection: How many users put it in "abandoned".
        shikimori: Entry on Shikimori.
        mal: Entry on MyAnimeList.
        rating: Score from AniLibria users.
        genres: Genres of the release.
        background_covers: Wide cover images for a page background.
        members: People who worked on the release.
        sponsors: Sponsors shown on the release page.
        episodes: All episodes of the release, in order.
        latest_episode: The newest episode — only filled in by ``client.releases.latest()``.
    """

    id: int
    alias: str
    name: ReleaseName
    type: Annotated[ValueDescription[str] | None, EMPTY_VALUE_AS_NONE] = None
    year: int | None = None
    season: Annotated[ValueDescription[str] | None, EMPTY_VALUE_AS_NONE] = None
    poster: Image | None = None
    description: str | None = None
    notification: str | None = None
    age_rating: Annotated[AgeRating | None, EMPTY_VALUE_AS_NONE] = None
    publish_day: Annotated[ValueDescription[int] | None, EMPTY_VALUE_AS_NONE] = None
    is_ongoing: bool
    is_in_production: bool
    is_blocked_by_geo: bool
    is_blocked_by_copyrights: bool
    episodes_total: int | None = None
    average_duration_of_episode: int | None = None
    external_player: str | None = None
    fresh_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    added_in_users_favorites: int
    added_in_planned_collection: int
    added_in_watched_collection: int
    added_in_watching_collection: int
    added_in_postponed_collection: int
    added_in_abandoned_collection: int
    shikimori: ExternalRating | None = None
    mal: ExternalRating | None = None
    rating: ReleaseRating | None = None
    genres: list[Genre] = Field(default_factory=list)
    background_covers: list[ImageSet] = Field(default_factory=list)
    members: list[ReleaseMember] = Field(default_factory=list)
    sponsors: list[Sponsor] = Field(default_factory=list)
    episodes: list[Episode] = Field(default_factory=list)
    latest_episode: Episode | None = None


# Episode.release refers back to Release, which only exists once this module has run.
Episode.model_rebuild(_types_namespace={"Release": Release})
