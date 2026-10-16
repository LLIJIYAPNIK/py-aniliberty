"""Page[T] parsing and iterate_pages."""

from __future__ import annotations

from typing import Any

import pydantic
import pytest

from aniliberty import Page
from aniliberty.pagination import iterate_pages


def envelope(items: list[Any], *, page: int, total_pages: int, limit: int = 2) -> dict[str, Any]:
    """A paginated response in the shape the API returns (docs/api-notes.md, "Pagination")."""
    return {
        "data": items,
        "meta": {
            "pagination": {
                "total": total_pages * limit,
                "count": len(items),
                "per_page": limit,
                "current_page": page,
                "total_pages": total_pages,
                "links": {"previous": None, "next": None},
            }
        },
    }


def test_page_is_built_from_the_api_envelope() -> None:
    page = Page[int].model_validate(envelope([1, 2], page=2, total_pages=3))

    assert page.items == [1, 2]
    assert (page.page, page.limit, page.total, page.total_pages) == (2, 2, 6, 3)
    assert page.has_next_page


def test_last_page_has_no_next_page() -> None:
    assert not Page[int].model_validate(envelope([5], page=3, total_pages=3)).has_next_page


def test_empty_result_has_no_next_page() -> None:
    page = Page[int].model_validate(envelope([], page=1, total_pages=0))
    assert page.items == []
    assert not page.has_next_page


def test_items_are_validated_as_the_page_type() -> None:
    with pytest.raises(pydantic.ValidationError):
        Page[int].model_validate(envelope(["not a number"], page=1, total_pages=1))


@pytest.mark.parametrize(
    "data",
    [
        {"data": [1]},
        {"data": [1], "meta": {}},
        {"data": [1], "meta": "broken"},
    ],
)
def test_missing_pagination_meta_is_a_validation_error(data: dict[str, Any]) -> None:
    with pytest.raises(pydantic.ValidationError):
        Page[int].model_validate(data)


def test_page_can_be_built_from_its_own_fields() -> None:
    page = Page[str](items=["a"], page=1, limit=10, total=1, total_pages=1)
    assert page.items == ["a"]


class FakeEndpoint:
    """Serves pages from a list; records which page numbers were requested."""

    def __init__(self, pages: list[list[int]], *, total_pages: int | None = None) -> None:
        self.pages = pages
        self.total_pages = len(pages) if total_pages is None else total_pages
        self.requested: list[int] = []

    async def __call__(self, page: int) -> Page[int]:
        self.requested.append(page)
        items = self.pages[page - 1] if page <= len(self.pages) else []
        return Page[int].model_validate(envelope(items, page=page, total_pages=self.total_pages))


async def collect(endpoint: FakeEndpoint, **kwargs: Any) -> list[int]:
    return [item async for item in iterate_pages(endpoint, **kwargs)]


async def test_iterates_over_all_pages_in_order() -> None:
    endpoint = FakeEndpoint([[1, 2], [3, 4], [5]])

    assert await collect(endpoint) == [1, 2, 3, 4, 5]
    assert endpoint.requested == [1, 2, 3]


async def test_single_page() -> None:
    endpoint = FakeEndpoint([[1]])
    assert await collect(endpoint) == [1]
    assert endpoint.requested == [1]


async def test_empty_first_page() -> None:
    endpoint = FakeEndpoint([[]])
    assert await collect(endpoint) == []
    assert endpoint.requested == [1]


async def test_stops_at_an_empty_page_even_if_total_pages_says_more() -> None:
    # total_pages can go stale while iterating (items deleted on the server).
    endpoint = FakeEndpoint([[1, 2], []], total_pages=5)

    assert await collect(endpoint) == [1, 2]
    assert endpoint.requested == [1, 2]


async def test_start_page() -> None:
    endpoint = FakeEndpoint([[1], [2], [3]])
    assert await collect(endpoint, start_page=2) == [2, 3]


async def test_next_page_is_fetched_lazily() -> None:
    endpoint = FakeEndpoint([[1, 2], [3]])

    async for item in iterate_pages(endpoint):
        if item == 2:
            break

    assert endpoint.requested == [1]
