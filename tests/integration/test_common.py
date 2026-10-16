"""Pagination, query serialization and image URLs against recorded live responses.

No public resource covers these endpoints yet, so a minimal resource built on BaseResource
exercises the same code path (build_query → HttpClient → validation with site_url context)
that ``client.catalog``, ``client.genres`` and the rest will use.
"""

from __future__ import annotations

from typing import Any

import pytest

from aniliberty import AniLiberty, Image, Page
from aniliberty.models._base import AniLibertyModel
from aniliberty.pagination import iterate_pages
from aniliberty.resources._base import BaseResource


class Item(AniLibertyModel):
    id: int
    type: dict[str, Any] | None = None


class Genre(AniLibertyModel):
    id: int
    name: str
    image: Image


class Probe(BaseResource):
    async def catalog(self, *, page: int = 1, limit: int = 2, **filters: Any) -> Page[Item]:
        params = {"page": page, "limit": limit, "f": filters, "include": ["id", "type.value"]}
        return await self._get("/anime/catalog/releases", Page[Item], params=params)

    async def genres(self) -> list[Genre]:
        return await self._get("/anime/genres", list[Genre])


@pytest.mark.vcr
async def test_page_from_a_real_paginated_response() -> None:
    async with AniLiberty() as client:
        page = await Probe(client.http).catalog(page=2, limit=3)

    assert page.page == 2
    assert page.limit == 3
    assert len(page.items) == 3
    assert page.total_pages == -(-page.total // 3)  # ceil
    assert page.has_next_page


@pytest.mark.vcr
async def test_list_filters_are_sent_comma_separated() -> None:
    async with AniLiberty() as client:
        page = await Probe(client.http).catalog(limit=50, types=["WEB", "MOVIE"])

    types = {item.type["value"] for item in page.items if item.type}
    assert types <= {"WEB", "MOVIE"}
    assert len(types) == 2  # both values of the list were applied, not just one


@pytest.mark.vcr
async def test_iterate_pages_over_real_pages() -> None:
    async with AniLiberty() as client:
        probe = Probe(client.http)

        async def fetch(page: int) -> Page[Item]:
            return await probe.catalog(page=page, limit=2, years={"from_year": 2025})

        ids: list[int] = []
        async for item in iterate_pages(fetch):
            ids.append(item.id)
            if len(ids) == 5:
                break

    assert len(ids) == 5
    assert len(set(ids)) == 5  # three different pages, no repeats


@pytest.mark.vcr
async def test_image_urls_point_to_the_host_the_client_used() -> None:
    async with AniLiberty(base_url="https://anilibria.top/api/v1") as client:
        genres = await Probe(client.http).genres()

    image = genres[0].image
    assert image.preview is not None
    assert image.preview.startswith("/storage/")
    assert image.preview_url == f"https://anilibria.top{image.preview}"
    assert image.optimized is not None
    assert image.optimized.preview_url is not None
    assert image.optimized.preview_url.startswith("https://anilibria.top/storage/")
