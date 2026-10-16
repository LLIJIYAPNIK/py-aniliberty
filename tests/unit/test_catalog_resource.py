"""client.catalog.releases / iter_releases: filter serialization and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, get_args

import httpx
import pytest

from aniliberty import AniLiberty, Genre, SortingOption, ValueDescription
from aniliberty.models.catalog import (
    AgeRatingValue,
    CatalogSorting,
    ProductionStatus,
    PublishStatus,
    ReleaseType,
    Season,
)

SPEC = json.loads((Path(__file__).parents[2] / "spec" / "openapi.json").read_text("utf-8"))
EMPTY_PAGE = {
    "data": [],
    "meta": {"pagination": {"total": 0, "per_page": 10, "current_page": 1, "total_pages": 0}},
}


@pytest.mark.parametrize(
    ("literal", "schema"),
    [
        (ReleaseType, "enums.anime.releases.release.type"),
        (Season, "enums.anime.releases.release.season"),
        (AgeRatingValue, "enums.anime.releases.release.ageRating"),
        (PublishStatus, "enums.anime.catalog.filter.publishStatus"),
        (ProductionStatus, "enums.anime.catalog.filter.productionStatus"),
        (CatalogSorting, "enums.anime.catalog.filter.sorting"),
    ],
)
def test_filter_literals_match_the_spec_enums(literal: Any, schema: str) -> None:
    assert list(get_args(literal)) == SPEC["components"]["schemas"][schema]["enum"]


class Recorder:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, json=EMPTY_PAGE)


async def sent_params(**kwargs: Any) -> dict[str, str]:
    recorder = Recorder()
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(recorder))
    async with AniLiberty(http_client=http_client) as client:
        await client.catalog.releases(**kwargs)
    await http_client.aclose()
    return dict(recorder.requests[0].url.params)


async def test_no_filters_sends_no_parameters() -> None:
    assert await sent_params() == {}


async def test_all_filters_are_serialized_as_the_api_expects() -> None:
    params = await sent_params(
        genres=[14, 29],
        types=["TV", "MOVIE"],
        seasons=["winter"],
        year_from=2016,
        year_to=2020,
        search="Мастера меча",
        sorting="RATING_DESC",
        age_ratings=["R6_PLUS", "R12_PLUS"],
        publish_statuses=["IS_ONGOING"],
        production_statuses=["IS_IN_PRODUCTION"],
        page=2,
        limit=25,
    )

    assert params == {
        "f[genres]": "14,29",
        "f[types]": "TV,MOVIE",
        "f[seasons]": "winter",
        "f[years][from_year]": "2016",
        "f[years][to_year]": "2020",
        "f[search]": "Мастера меча",
        "f[sorting]": "RATING_DESC",
        "f[age_ratings]": "R6_PLUS,R12_PLUS",
        "f[publish_statuses]": "IS_ONGOING",
        "f[production_statuses]": "IS_IN_PRODUCTION",
        "page": "2",
        "limit": "25",
    }


async def test_reference_items_are_accepted_as_filter_values() -> None:
    params = await sent_params(
        genres=[Genre(id=14, name="Экшен")],
        types=[ValueDescription[str](value="TV", description="ТВ")],
        sorting=SortingOption(value="YEAR_ASC", label="Самые старые"),
    )

    assert params == {"f[genres]": "14", "f[types]": "TV", "f[sorting]": "YEAR_ASC"}


async def test_only_one_year_bound() -> None:
    assert await sent_params(year_to=2000) == {"f[years][to_year]": "2000"}


@pytest.mark.parametrize(
    ("kwargs", "error", "match"),
    [
        ({"types": ["FOO"]}, ValueError, "Unknown types value 'FOO'"),
        ({"seasons": ["Winter"]}, ValueError, "Unknown seasons value 'Winter'"),
        ({"sorting": "NEWEST"}, ValueError, "Unknown sorting value 'NEWEST'"),
        ({"age_ratings": ["16+"]}, ValueError, "Unknown age_ratings value"),
        ({"publish_statuses": ["ONGOING"]}, ValueError, "Unknown publish_statuses value"),
        ({"production_statuses": ["x"]}, ValueError, "Unknown production_statuses value"),
        ({"types": "TV"}, TypeError, r"types must be a list, e\.g\. types=\['TV'\]"),
        ({"genres": ["14"]}, TypeError, "genres must be genre IDs"),
        ({"genres": [True]}, TypeError, "genres must be genre IDs"),
        ({"year_from": "2020"}, TypeError, "year_from must be an int"),
        ({"year_to": 2020.0}, TypeError, "year_to must be an int"),
        ({"year_from": 2022, "year_to": 2020}, ValueError, "year_from .* is after year_to"),
    ],
)
async def test_invalid_filters_fail_before_sending(
    kwargs: dict[str, Any], error: type[Exception], match: str
) -> None:
    recorder = Recorder()
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(recorder))
    async with AniLiberty(http_client=http_client) as client:
        with pytest.raises(error, match=match):
            await client.catalog.releases(**kwargs)
        with pytest.raises(error, match=match):
            client.catalog.iter_releases(**kwargs)  # raised right away, not on iteration
    await http_client.aclose()

    assert recorder.requests == []


async def test_iter_releases_pages_through_with_the_same_filters() -> None:
    def page(number: int, ids: list[int]) -> dict[str, Any]:
        release = {
            "alias": "a",
            "name": {"main": "Название"},
            "is_ongoing": True,
            "is_in_production": True,
            "is_blocked_by_geo": False,
            "is_blocked_by_copyrights": False,
            "added_in_users_favorites": 0,
            "added_in_planned_collection": 0,
            "added_in_watched_collection": 0,
            "added_in_watching_collection": 0,
            "added_in_postponed_collection": 0,
            "added_in_abandoned_collection": 0,
        }
        return {
            "data": [{**release, "id": i} for i in ids],
            "meta": {
                "pagination": {"total": 3, "per_page": 2, "current_page": number, "total_pages": 2}
            },
        }

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        number = int(request.url.params["page"])
        return httpx.Response(200, json=page(number, [1, 2] if number == 1 else [3]))

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with AniLiberty(http_client=http_client) as client:
        ids = [r.id async for r in client.catalog.iter_releases(types=["TV"], limit=2)]
    await http_client.aclose()

    assert ids == [1, 2, 3]
    assert [r.url.params["page"] for r in requests] == ["1", "2"]
    assert all(r.url.params["f[types]"] == "TV" and r.url.params["limit"] == "2" for r in requests)
