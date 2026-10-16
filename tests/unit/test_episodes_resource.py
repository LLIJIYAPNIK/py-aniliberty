"""Episode model on edge-case JSON and client.episodes argument handling."""

from __future__ import annotations

from typing import Any

import httpx
import pydantic
import pytest

from aniliberty import AniLiberty, Episode, Release, SkipRange
from aniliberty.resources._base import path_segment

EPISODE: dict[str, Any] = {
    "id": "9b5e26ee-598f-4b8b-b77e-188d3e456318",
    "release_id": 9324,
    "ordinal": 12,
    "sort_order": 12,
    "duration": 1432,
    "name": None,
    "name_english": None,
    "opening": {"start": None, "stop": None},
    "ending": {"start": 1325, "stop": 1415},
    "preview": {"preview": None, "thumbnail": None, "optimized": {"preview": None}},
    "hls_480": "https://cache.libria.fun/videos/media/ts/9324/12/480/a.m3u8?countryIso=NL",
    "hls_720": "https://cache.libria.fun/videos/media/ts/9324/12/720/b.m3u8?countryIso=NL",
    "hls_1080": None,
    "rutube_id": None,
    "youtube_id": None,
    "updated_at": "2021-11-25T18:46:30+00:00",
}


def test_episode_fields() -> None:
    episode = Episode.model_validate(EPISODE)

    assert episode.opening is None  # {"start": null, "stop": null} means "not marked"
    assert episode.ending == SkipRange(start=1325, stop=1415)
    assert episode.hls_1080 is None
    assert episode.hls_720 == EPISODE["hls_720"]  # query string kept as is
    assert episode.updated_at is not None
    assert episode.updated_at.tzinfo is not None
    assert episode.release is None


@pytest.mark.parametrize(("raw", "expected"), [(12, 12), (12.5, 12.5)])
def test_ordinal_keeps_ints_and_fractions(raw: float, expected: float) -> None:
    ordinal = Episode.model_validate({**EPISODE, "ordinal": raw}).ordinal
    assert ordinal == expected
    assert type(ordinal) is type(raw)


def test_missing_skip_ranges_are_none() -> None:
    data = {k: v for k, v in EPISODE.items() if k not in ("opening", "ending")}
    episode = Episode.model_validate(data)
    assert episode.opening is None
    assert episode.ending is None


@pytest.mark.parametrize("field", ["id", "release_id", "ordinal", "sort_order", "duration"])
def test_required_fields(field: str) -> None:
    data = {k: v for k, v in EPISODE.items() if k != field}
    with pytest.raises(pydantic.ValidationError, match=field):
        Episode.model_validate(data)


def test_episode_embeds_release_with_episodes() -> None:
    release = {
        "id": 9324,
        "alias": "a",
        "name": {"main": "Название"},
        "is_ongoing": False,
        "is_in_production": False,
        "is_blocked_by_geo": False,
        "is_blocked_by_copyrights": False,
        "added_in_users_favorites": 0,
        "added_in_planned_collection": 0,
        "added_in_watched_collection": 0,
        "added_in_watching_collection": 0,
        "added_in_postponed_collection": 0,
        "added_in_abandoned_collection": 0,
        "episodes": [EPISODE],
    }
    episode = Episode.model_validate({**EPISODE, "release": release})

    assert isinstance(episode.release, Release)
    assert episode.release.episodes[0].id == EPISODE["id"]


async def test_get_requests_the_episode_path() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=EPISODE)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with AniLiberty(http_client=http_client) as client:
        episode = await client.episodes.get(EPISODE["id"])

    assert seen[0].url.path == f"/api/v1/anime/releases/episodes/{EPISODE['id']}"
    assert episode.id == EPISODE["id"]
    await http_client.aclose()


@pytest.mark.parametrize("bad", ["", "a/b", "..", 5.0, None])
async def test_get_rejects_invalid_ids_before_sending(bad: Any) -> None:
    async with AniLiberty() as client:
        with pytest.raises((TypeError, ValueError), match="episode ID"):
            await client.episodes.get(bad)


def test_path_segment_accepts_ints_and_strings() -> None:
    assert path_segment(10, what="ID") == "10"
    assert path_segment("naruto", what="alias") == "naruto"
