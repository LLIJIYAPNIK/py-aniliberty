"""client.releases: argument handling, request shape and the Release model on edge-case JSON."""

from __future__ import annotations

from typing import Any

import httpx
import pydantic
import pytest

from aniliberty import AniLiberty, Release
from aniliberty.resources import CatalogReferencesResource, CatalogResource

MINIMAL_RELEASE: dict[str, Any] = {
    "id": 1,
    "alias": "some-alias",
    "name": {"main": "Название", "english": None, "alternative": None},
    "is_ongoing": False,
    "is_in_production": False,
    "is_blocked_by_geo": False,
    "is_blocked_by_copyrights": False,
    "added_in_users_favorites": 10,
    "added_in_planned_collection": 1,
    "added_in_watched_collection": 2,
    "added_in_watching_collection": 3,
    "added_in_postponed_collection": 4,
    "added_in_abandoned_collection": 5,
}


class Recorder:
    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, json=self.payload)


def make_client(recorder: Recorder) -> AniLiberty:
    return AniLiberty(http_client=httpx.AsyncClient(transport=httpx.MockTransport(recorder)))


def test_minimal_release_has_empty_extras() -> None:
    release = Release.model_validate(MINIMAL_RELEASE)

    assert release.genres == []
    assert release.members == []
    assert release.sponsors == []
    assert release.background_covers == []
    assert release.season is None
    assert release.poster is None
    assert release.name.alternative is None


def test_empty_season_object_becomes_none() -> None:
    release = Release.model_validate(
        {**MINIMAL_RELEASE, "season": {"value": None, "description": None}}
    )
    assert release.season is None


def test_rating_distribution_keys_become_ints() -> None:
    rating = {"average": None, "votes": 0, "distribution": {str(i): 0 for i in range(1, 11)}}
    release = Release.model_validate({**MINIMAL_RELEASE, "rating": rating})

    assert release.rating is not None
    assert release.rating.average is None
    assert list(release.rating.distribution) == list(range(1, 11))


def test_missing_counter_is_a_validation_error_not_a_zero() -> None:
    data = dict(MINIMAL_RELEASE)
    del data["added_in_users_favorites"]
    with pytest.raises(pydantic.ValidationError, match="added_in_users_favorites"):
        Release.model_validate(data)


async def test_list_sends_ids_and_aliases_comma_separated() -> None:
    page = {
        "data": [MINIMAL_RELEASE],
        "meta": {"pagination": {"total": 1, "per_page": 5, "current_page": 1, "total_pages": 1}},
    }
    recorder = Recorder(page)
    async with make_client(recorder) as client:
        result = await client.releases.list(ids=[1, 2], aliases=["a", "b"], page=1, limit=5)

    params = recorder.requests[0].url.params
    assert params["ids"] == "1,2"
    assert params["aliases"] == "a,b"
    assert params["page"] == "1"
    assert params["limit"] == "5"
    assert result.items[0].id == 1


async def test_optional_params_are_not_sent() -> None:
    recorder = Recorder([])
    async with make_client(recorder) as client:
        await client.releases.recommended()

    assert recorder.requests[0].url.query == b""


async def test_release_objects_are_accepted_wherever_a_release_is_identified() -> None:
    release = Release.model_validate({**MINIMAL_RELEASE, "id": 9542})
    recorder = Recorder([])
    async with make_client(recorder) as client:
        recorder.payload = MINIMAL_RELEASE
        await client.releases.get(release)
        recorder.payload = []
        await client.releases.members(release)
        await client.releases.timecodes(release)
        await client.releases.recommended(release=release)

    paths = [request.url.path for request in recorder.requests]
    assert paths[:3] == [
        "/api/v1/anime/releases/9542",
        "/api/v1/anime/releases/9542/members",
        "/api/v1/anime/releases/9542/episodes/timecodes",
    ]
    assert recorder.requests[3].url.params["release_id"] == "9542"


@pytest.mark.parametrize("bad", ["sousou-no-frieren", True])
async def test_recommended_takes_only_numeric_ids(bad: Any) -> None:
    recorder = Recorder([])
    async with make_client(recorder) as client:
        with pytest.raises(TypeError, match="Expected a release ID"):
            await client.releases.recommended(release=bad)

    assert recorder.requests == []


@pytest.mark.parametrize("kwargs", [{}, {"ids": []}, {"aliases": []}])
async def test_list_requires_ids_or_aliases(kwargs: dict[str, Any]) -> None:
    async with AniLiberty() as client:
        with pytest.raises(ValueError, match="ids, aliases"):
            await client.releases.list(**kwargs)
        with pytest.raises(ValueError, match="ids, aliases"):
            client.releases.iter_list(**kwargs)


@pytest.mark.parametrize("bad", ["", "a/b", "..", ".", True, 1.5, None])
async def test_get_rejects_invalid_ids_before_sending(bad: Any) -> None:
    recorder = Recorder({})
    async with make_client(recorder) as client:
        with pytest.raises((ValueError, TypeError)):
            await client.releases.get(bad)
        with pytest.raises((ValueError, TypeError)):
            await client.releases.members(bad)

    assert recorder.requests == []


def test_catalog_namespace_has_references() -> None:
    client = AniLiberty()
    assert isinstance(client.catalog, CatalogResource)
    assert isinstance(client.catalog.references, CatalogReferencesResource)
