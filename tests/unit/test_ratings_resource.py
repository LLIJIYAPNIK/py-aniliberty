"""client.releases.ratings: paths, bodies, argument checks."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from aniliberty import AniLiberty, Release, UserRating

RATING = "/api/v1/anime/releases/8030/rating"


class FakeApi:
    def __init__(self, body: Any) -> None:
        self.body = body
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, json=self.body)


async def call(api: FakeApi, method: str, *args: Any, **kwargs: Any) -> Any:
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(api))
    async with AniLiberty(http_client=http_client, token="t0k3n") as client:
        result = await getattr(client.releases.ratings, method)(*args, **kwargs)
    await http_client.aclose()
    return result


def release(release_id: int) -> Release:
    return Release.model_validate(
        {
            "id": release_id,
            "alias": "tate-no-yuusha-no-nariagari",
            "name": {"main": "Восхождение героя щита"},
            "is_ongoing": False,
            "is_in_production": False,
            "is_blocked_by_geo": False,
            "is_blocked_by_copyrights": False,
            "added_in_users_favorites": 1,
            "added_in_planned_collection": 1,
            "added_in_watched_collection": 1,
            "added_in_watching_collection": 1,
            "added_in_postponed_collection": 1,
            "added_in_abandoned_collection": 1,
        }
    )


async def test_get_without_a_score() -> None:
    api = FakeApi({"release_id": 8030, "score": None})

    rating = await call(api, "get", 8030)

    assert rating == UserRating(release_id=8030, score=None)
    request = api.requests[0]
    assert (request.method, request.url.path) == ("GET", RATING)
    assert request.headers["Authorization"] == "Bearer t0k3n"


async def test_set_posts_the_score_and_accepts_a_release_object() -> None:
    api = FakeApi({"release_id": 8030, "score": 7})

    rating = await call(api, "set", release(8030), score=7)

    assert rating.score == 7
    request = api.requests[0]
    assert (request.method, request.url.path) == ("POST", RATING)
    assert json.loads(request.content) == {"score": 7}


async def test_remove_sends_a_delete() -> None:
    api = FakeApi({"release_id": 8030, "score": None})

    rating = await call(api, "remove", 8030)

    assert rating.score is None
    assert (api.requests[0].method, api.requests[0].url.path) == ("DELETE", RATING)
    assert api.requests[0].content == b""


@pytest.mark.parametrize("method", ["get", "remove"])
@pytest.mark.parametrize("bad", ["tate-no-yuusha-no-nariagari", "8030", True, 8030.0])
async def test_aliases_and_non_ints_are_rejected(method: str, bad: Any) -> None:
    api = FakeApi({})
    with pytest.raises(TypeError, match="Expected a release ID"):
        await call(api, method, bad)

    assert api.requests == []


@pytest.mark.parametrize(
    ("score", "error", "match"),
    [
        (0, ValueError, "from 1 to 10, got 0"),
        (11, ValueError, "from 1 to 10, got 11"),
        (7.5, TypeError, "must be an int"),
        ("7", TypeError, "must be an int"),
        (True, TypeError, "must be an int"),
        (None, TypeError, "must be an int"),
    ],
)
async def test_set_checks_the_score_before_sending(
    score: Any, error: type[Exception], match: str
) -> None:
    api = FakeApi({})
    with pytest.raises(error, match=match):
        await call(api, "set", 8030, score=score)

    assert api.requests == []


@pytest.mark.parametrize("score", [1, 10])
async def test_set_accepts_both_bounds(score: int) -> None:
    api = FakeApi({"release_id": 8030, "score": score})

    assert (await call(api, "set", 8030, score=score)).score == score
