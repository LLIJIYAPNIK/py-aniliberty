"""client.genres: argument handling and request shape."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from aniliberty import AniLiberty, Genre

EMPTY_PAGE = {
    "data": [],
    "meta": {"pagination": {"total": 0, "per_page": 15, "current_page": 1, "total_pages": 0}},
}


async def requested(method: str, *args: Any, payload: Any = None, **kwargs: Any) -> httpx.Request:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=payload)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with AniLiberty(http_client=http_client) as client:
        await getattr(client.genres, method)(*args, **kwargs)
    await http_client.aclose()
    return seen[0]


async def test_genre_object_is_accepted_wherever_an_id_is() -> None:
    genre = Genre(id=14, name="Экшен")
    single = await requested("get", genre, payload={"id": 14, "name": "Экшен"})
    page = await requested("releases", genre, page=2, limit=30, payload=EMPTY_PAGE)

    assert single.url.path == "/api/v1/anime/genres/14"
    assert page.url.path == "/api/v1/anime/genres/14/releases"
    assert dict(page.url.params) == {"page": "2", "limit": "30"}


async def test_random_without_limit_sends_no_parameters() -> None:
    request = await requested("random", payload=[])
    assert request.url.query == b""


@pytest.mark.parametrize("bad", ["14", 14.0, True, None])
async def test_invalid_genre_fails_before_sending(bad: Any) -> None:
    async with AniLiberty() as client:
        with pytest.raises(TypeError, match="genre ID or a Genre"):
            await client.genres.get(bad)
        with pytest.raises(TypeError, match="genre ID or a Genre"):
            await client.genres.releases(bad)
        with pytest.raises(TypeError, match="genre ID or a Genre"):
            client.genres.iter_releases(bad)  # raised right away, not on iteration
