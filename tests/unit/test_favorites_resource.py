"""client.me.favorites: request bodies, filter serialization and validation, references."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, get_args

import httpx
import pytest

from aniliberty import AniLiberty, Genre, Release, SortingOption
from aniliberty.models import FavoritesSorting

SPEC = json.loads((Path(__file__).parents[2] / "spec" / "openapi.json").read_text("utf-8"))
FAVORITES = "/api/v1/accounts/users/me/favorites"


def release(release_id: int) -> dict[str, Any]:
    return {
        "id": release_id,
        "alias": f"r{release_id}",
        "name": {"main": f"Релиз {release_id}"},
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


def page(items: list[dict[str, Any]], *, current: int, pages: int) -> dict[str, Any]:
    return {
        "data": items,
        "meta": {
            "pagination": {
                "total": 3,
                "count": len(items),
                "per_page": 2,
                "current_page": current,
                "total_pages": pages,
            }
        },
    }


class FakeApi:
    def __init__(self, respond: Any = None) -> None:
        self.requests: list[httpx.Request] = []
        self.respond = respond or (lambda request: httpx.Response(200, json=[]))

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        response: httpx.Response = self.respond(request)
        return response


async def call(api: FakeApi, method: str, *args: Any, **kwargs: Any) -> Any:
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(api))
    async with AniLiberty(http_client=http_client, token="t0k3n") as client:
        target: Any = client.me.favorites
        for name in method.split("."):
            target = getattr(target, name)
        result = await target(*args, **kwargs)
    await http_client.aclose()
    return result


def empty_page(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=page([], current=1, pages=1))


async def sent_params(**kwargs: Any) -> dict[str, str]:
    api = FakeApi(empty_page)
    await call(api, "releases", **kwargs)
    return dict(api.requests[0].url.params)


def test_sorting_literal_matches_the_spec_enum() -> None:
    schema = SPEC["components"]["schemas"]["enums.accounts.users.user.favorite.filter.sorting"]
    assert list(get_args(FavoritesSorting)) == schema["enum"]


# --- ids, add, remove -----------------------------------------------------------------------


async def test_ids() -> None:
    api = FakeApi(lambda request: httpx.Response(200, json=[9839, 8030]))

    assert await call(api, "ids") == [9839, 8030]
    assert api.requests[0].method == "GET"
    assert api.requests[0].url.path == f"{FAVORITES}/ids"
    assert api.requests[0].headers["Authorization"] == "Bearer t0k3n"


async def test_add_takes_ids_and_release_objects_and_returns_all_ids() -> None:
    api = FakeApi(lambda request: httpx.Response(200, json=[1, 9839, 8030]))
    obj = Release.model_validate(release(8030))

    assert await call(api, "add", 9839, obj) == [1, 9839, 8030]
    request = api.requests[0]
    assert request.method == "POST"
    assert request.url.path == FAVORITES
    assert json.loads(request.content) == [{"release_id": 9839}, {"release_id": 8030}]


async def test_remove_sends_a_delete_with_a_body() -> None:
    api = FakeApi(lambda request: httpx.Response(200, json=[1]))

    assert await call(api, "remove", 9839) == [1]
    request = api.requests[0]
    assert request.method == "DELETE"
    assert request.url.path == FAVORITES
    assert json.loads(request.content) == [{"release_id": 9839}]


@pytest.mark.parametrize("method", ["add", "remove"])
async def test_add_and_remove_need_at_least_one_release(method: str) -> None:
    api = FakeApi()
    with pytest.raises(ValueError, match="at least one release"):
        await call(api, method)

    assert api.requests == []


@pytest.mark.parametrize("bad", ["9839", True, 1.5, None])
async def test_add_rejects_values_that_are_not_release_ids(bad: Any) -> None:
    api = FakeApi()
    with pytest.raises(TypeError, match="release ID or a Release"):
        await call(api, "add", 1, bad)

    assert api.requests == []


# --- releases -------------------------------------------------------------------------------


async def test_no_filters_sends_no_parameters() -> None:
    assert await sent_params() == {}


async def test_all_filters_are_serialized_as_the_api_expects() -> None:
    params = await sent_params(
        genres=[14, Genre(id=27, name="Приключения")],
        types=["TV", "MOVIE"],
        years=range(2019, 2022),
        search="Подняти",
        sorting=SortingOption(value="YEAR_DESC"),
        age_ratings=["R16_PLUS"],
        page=2,
        limit=50,
    )

    assert params == {
        "f[genres]": "14,27",
        "f[types]": "TV,MOVIE",
        "f[years]": "2019,2020,2021",
        "f[search]": "Подняти",
        "f[sorting]": "YEAR_DESC",
        "f[age_ratings]": "R16_PLUS",
        "page": "2",
        "limit": "50",
    }


@pytest.mark.parametrize(
    ("kwargs", "error", "match"),
    [
        ({"types": ["FOO"]}, ValueError, "Unknown types value 'FOO'"),
        ({"sorting": "BOGUS"}, ValueError, "Unknown sorting value 'BOGUS'"),
        # A catalog-only sort order isn't valid here, and vice versa.
        ({"sorting": "CREATED_AT"}, ValueError, "Unknown sorting value"),
        ({"age_ratings": ["16+"]}, ValueError, "Unknown age_ratings value"),
        ({"types": "TV"}, TypeError, "types must be a list"),
        ({"years": 2024}, TypeError, "years must be a list"),
        ({"years": "2024"}, TypeError, "years must be a list"),
        ({"years": [2024, "2025"]}, TypeError, "years must be ints"),
        ({"years": [True]}, TypeError, "years must be ints"),
        ({"genres": ["14"]}, TypeError, "genres must be genre IDs"),
    ],
)
async def test_invalid_filters_raise_before_any_request(
    kwargs: dict[str, Any], error: type[Exception], match: str
) -> None:
    api = FakeApi(empty_page)
    with pytest.raises(error, match=match):
        await call(api, "releases", **kwargs)

    assert api.requests == []


async def test_iter_releases_walks_all_pages_with_the_same_filters() -> None:
    pages = {
        "1": page([release(1), release(2)], current=1, pages=2),
        "2": page([release(3)], current=2, pages=2),
    }
    api = FakeApi(lambda request: httpx.Response(200, json=pages[request.url.params["page"]]))
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(api))
    async with AniLiberty(http_client=http_client, token="t0k3n") as client:
        ids = [r.id async for r in client.me.favorites.iter_releases(types=["TV"], limit=2)]
    await http_client.aclose()

    assert ids == [1, 2, 3]
    assert [r.url.params["page"] for r in api.requests] == ["1", "2"]
    assert {r.url.params["f[types]"] for r in api.requests} == {"TV"}
    assert {r.url.params["limit"] for r in api.requests} == {"2"}


def test_iter_releases_validates_filters_right_away() -> None:
    client = AniLiberty(token="t0k3n")
    with pytest.raises(ValueError, match="Unknown sorting value"):
        client.me.favorites.iter_releases(sorting="NEWEST")  # type: ignore[arg-type]


# --- references -----------------------------------------------------------------------------

REFERENCES = {
    "genres": ([{"id": 16, "name": "Демоны"}], lambda r: r[0].name == "Демоны"),
    "types": ([{"value": "TV", "description": "ТВ"}], lambda r: r[0].value == "TV"),
    "years": ([2025, 2024], lambda r: r == [2025, 2024]),
    "age_ratings": (
        [{"value": "R16_PLUS", "label": "16+", "description": "16+"}],
        lambda r: r[0].label == "16+",
    ),
    "sorting": (
        [{"value": "CREATED_AT_DESC", "label": "Добавлены недавно", "description": "..."}],
        lambda r: r[0].value == "CREATED_AT_DESC",
    ),
}


@pytest.mark.parametrize("name", list(REFERENCES))
async def test_references(name: str) -> None:
    body, check = REFERENCES[name]
    api = FakeApi(lambda request: httpx.Response(200, json=body))

    result = await call(api, f"references.{name}")

    assert check(result)
    assert api.requests[0].url.path == f"{FAVORITES}/references/{name.replace('_', '-')}"
