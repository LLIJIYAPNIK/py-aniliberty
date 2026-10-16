"""client.me.collections: the [id, type] pairs, request bodies, filters, references."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, get_args

import httpx
import pydantic
import pytest

from aniliberty import AniLiberty, CollectionItem, Release
from aniliberty.models import CollectionType

SPEC = json.loads((Path(__file__).parents[2] / "spec" / "openapi.json").read_text("utf-8"))
COLLECTIONS = "/api/v1/accounts/users/me/collections"
PAIRS = [[9839, "WATCHED"], [8030, "PLANNED"]]


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
    pagination = {"total": 3, "per_page": 2, "current_page": current, "total_pages": pages}
    return {"data": items, "meta": {"pagination": pagination}}


class FakeApi:
    def __init__(self, body: Any = None, respond: Any = None) -> None:
        self.requests: list[httpx.Request] = []
        self.respond = respond or (lambda request: httpx.Response(200, json=body))

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        response: httpx.Response = self.respond(request)
        return response


async def call(api: FakeApi, method: str, *args: Any, **kwargs: Any) -> Any:
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(api))
    async with AniLiberty(http_client=http_client, token="t0k3n") as client:
        target: Any = client.me.collections
        for name in method.split("."):
            target = getattr(target, name)
        result = await target(*args, **kwargs)
    await http_client.aclose()
    return result


def test_collection_type_literal_matches_the_spec_enum() -> None:
    schema = SPEC["components"]["schemas"]["enums.accounts.users.user.collection.type"]
    assert list(get_args(CollectionType)) == schema["enum"]


# --- CollectionItem -------------------------------------------------------------------------


def test_item_is_validated_from_the_api_pair_or_a_dict() -> None:
    from_pair = CollectionItem.model_validate([9839, "WATCHED"])
    from_dict = CollectionItem.model_validate({"release_id": 9839, "collection": "WATCHED"})

    assert from_pair == from_dict == CollectionItem(release_id=9839, collection="WATCHED")


@pytest.mark.parametrize("bad", [[9839], [9839, "WATCHED", 1], [9839, "watched"], "x"])
def test_malformed_items_are_rejected(bad: Any) -> None:
    with pytest.raises(pydantic.ValidationError):
        CollectionItem.model_validate(bad)


# --- ids, add, remove -----------------------------------------------------------------------


async def test_ids_parses_the_pairs() -> None:
    api = FakeApi(PAIRS)

    items = await call(api, "ids")

    assert items == [
        CollectionItem(release_id=9839, collection="WATCHED"),
        CollectionItem(release_id=8030, collection="PLANNED"),
    ]
    assert api.requests[0].url.path == f"{COLLECTIONS}/ids"
    assert api.requests[0].headers["Authorization"] == "Bearer t0k3n"


async def test_add_sends_each_release_with_the_collection() -> None:
    api = FakeApi(PAIRS)
    obj = Release.model_validate(release(8030))

    items = await call(api, "add", 9839, obj, to="WATCHING")

    assert [item.release_id for item in items] == [9839, 8030]
    request = api.requests[0]
    assert request.method == "POST"
    assert request.url.path == COLLECTIONS
    assert json.loads(request.content) == [
        {"release_id": 9839, "type_of_collection": "WATCHING"},
        {"release_id": 8030, "type_of_collection": "WATCHING"},
    ]


async def test_remove_sends_only_the_release_ids() -> None:
    api = FakeApi([[8030, "PLANNED"]])

    items = await call(api, "remove", 9839)

    assert items == [CollectionItem(release_id=8030, collection="PLANNED")]
    request = api.requests[0]
    assert request.method == "DELETE"
    assert json.loads(request.content) == [{"release_id": 9839}]


@pytest.mark.parametrize(
    ("args", "kwargs", "error", "match"),
    [
        ((), {"to": "PLANNED"}, ValueError, "at least one release"),
        ((1,), {"to": "planned"}, ValueError, "Unknown collection value 'planned'"),
        ((1,), {"to": "FAVORITES"}, ValueError, "Unknown collection value"),
        ((1, "2"), {"to": "PLANNED"}, TypeError, "release ID or a Release"),
    ],
)
async def test_add_checks_arguments_before_sending(
    args: tuple[Any, ...], kwargs: dict[str, Any], error: type[Exception], match: str
) -> None:
    api = FakeApi(PAIRS)
    with pytest.raises(error, match=match):
        await call(api, "add", *args, **kwargs)

    assert api.requests == []


async def test_remove_needs_at_least_one_release() -> None:
    api = FakeApi(PAIRS)
    with pytest.raises(ValueError, match="at least one release"):
        await call(api, "remove")

    assert api.requests == []


# --- releases -------------------------------------------------------------------------------


def empty_page(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=page([], current=1, pages=1))


async def sent_params(*args: Any, **kwargs: Any) -> dict[str, str]:
    api = FakeApi(respond=empty_page)
    await call(api, "releases", *args, **kwargs)
    return dict(api.requests[0].url.params)


async def test_collection_alone_is_sent_as_type_of_collection() -> None:
    assert await sent_params("WATCHED") == {"type_of_collection": "WATCHED"}


async def test_all_filters_are_serialized_as_the_api_expects() -> None:
    params = await sent_params(
        "PLANNED",
        genres=[14, 8],
        types=["TV"],
        years=[2024, 2019],
        search="Подняти",
        age_ratings=["R16_PLUS", "R18_PLUS"],
        page=2,
        limit=10,
    )

    assert params == {
        "type_of_collection": "PLANNED",
        "f[genres]": "14,8",
        "f[types]": "TV",
        "f[years]": "2024,2019",
        "f[search]": "Подняти",
        "f[age_ratings]": "R16_PLUS,R18_PLUS",
        "page": "2",
        "limit": "10",
    }


@pytest.mark.parametrize(
    ("args", "kwargs", "error", "match"),
    [
        (("planned",), {}, ValueError, "Unknown collection value"),
        (("PLANNED",), {"types": ["FOO"]}, ValueError, "Unknown types value"),
        (("PLANNED",), {"years": 2024}, TypeError, "years must be a list"),
        (("PLANNED",), {"age_ratings": "R16_PLUS"}, TypeError, "age_ratings must be a list"),
    ],
)
async def test_invalid_arguments_raise_before_any_request(
    args: tuple[Any, ...], kwargs: dict[str, Any], error: type[Exception], match: str
) -> None:
    api = FakeApi(respond=empty_page)
    with pytest.raises(error, match=match):
        await call(api, "releases", *args, **kwargs)

    assert api.requests == []


async def test_iter_releases_walks_all_pages_of_one_collection() -> None:
    pages = {
        "1": page([release(1), release(2)], current=1, pages=2),
        "2": page([release(3)], current=2, pages=2),
    }
    api = FakeApi(respond=lambda r: httpx.Response(200, json=pages[r.url.params["page"]]))
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(api))
    async with AniLiberty(http_client=http_client, token="t0k3n") as client:
        ids = [r.id async for r in client.me.collections.iter_releases("WATCHING", limit=2)]
    await http_client.aclose()

    assert ids == [1, 2, 3]
    assert {r.url.params["type_of_collection"] for r in api.requests} == {"WATCHING"}


def test_iter_releases_validates_the_collection_right_away() -> None:
    client = AniLiberty(token="t0k3n")
    with pytest.raises(ValueError, match="Unknown collection value"):
        client.me.collections.iter_releases("SEEN")  # type: ignore[arg-type]


# --- references -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "body"),
    [
        ("genres", [{"id": 16, "name": "Демоны"}]),
        ("types", [{"value": "TV", "description": "ТВ"}]),
        ("years", [2025, 2019]),
        ("age_ratings", [{"value": "R16_PLUS", "label": "16+", "description": "16+"}]),
    ],
)
async def test_references(name: str, body: list[Any]) -> None:
    api = FakeApi(body)

    result = await call(api, f"references.{name}")

    assert len(result) == len(body)
    assert api.requests[0].url.path == f"{COLLECTIONS}/references/{name.replace('_', '-')}"


def test_collections_have_no_sorting_reference() -> None:
    assert not hasattr(AniLiberty().me.collections.references, "sorting")
