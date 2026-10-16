"""client.franchises: argument handling and models on edge-case JSON."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from aniliberty import AniLiberty, Franchise

FRANCHISE: dict[str, Any] = {
    "id": "9f7649af-aeb9-42e8-8167-98bfa4eba36e",
    "name": "7 семян",
    "name_english": "7 Seeds",
    "rating": None,
    "first_year": None,
    "last_year": None,
    "total_releases": None,
    "total_episodes": None,
    "total_duration": None,
    "total_duration_in_seconds": 0,
    "image": {"preview": None, "thumbnail": None, "optimized": {"preview": None}},
}


def test_franchise_with_missing_totals() -> None:
    franchise = Franchise.model_validate(FRANCHISE)

    assert franchise.total_releases is None
    assert franchise.rating is None
    assert franchise.franchise_releases == []
    assert franchise.image is not None
    assert franchise.image.preview_url is None


async def requested(method: str, *args: Any, payload: Any) -> httpx.Request:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=payload)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with AniLiberty(http_client=http_client) as client:
        await getattr(client.franchises, method)(*args)
    await http_client.aclose()
    return seen[0]


async def test_get_accepts_a_franchise_object() -> None:
    request = await requested("get", Franchise.model_validate(FRANCHISE), payload=FRANCHISE)
    assert request.url.path == f"/api/v1/anime/franchises/{FRANCHISE['id']}"


async def test_for_release_uses_the_numeric_id() -> None:
    request = await requested("for_release", 9542, payload=[])
    assert request.url.path == "/api/v1/anime/franchises/release/9542"


@pytest.mark.parametrize("bad", ["sousou-no-frieren", "9542", True, None, 9542.0])
async def test_for_release_rejects_aliases_and_other_types(bad: Any) -> None:
    async with AniLiberty() as client:
        with pytest.raises(TypeError, match="aliases don't work here"):
            await client.franchises.for_release(bad)


@pytest.mark.parametrize(
    ("bad", "error"), [(123, TypeError), (None, TypeError), ("a/b", ValueError)]
)
async def test_get_rejects_invalid_ids(bad: Any, error: type[Exception]) -> None:
    async with AniLiberty() as client:
        with pytest.raises(error):
            await client.franchises.get(bad)
