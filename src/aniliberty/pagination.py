"""``Page[T]`` — one page of a paginated endpoint — and the helper behind ``iter_*`` methods."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Generic, TypeVar

from pydantic import model_validator

from aniliberty.models._base import AniLibertyModel

T = TypeVar("T")


class Page(AniLibertyModel, Generic[T]):
    """One page of results from a paginated endpoint.

    Paginated endpoints answer with ``{"data": [...], "meta": {"pagination": {...}}}`` (see
    ``docs/api-notes.md``); ``Page`` flattens that into the fields below. Pages are numbered
    from 1. To walk through all pages, use the matching ``iter_*()`` method instead of
    calling the paginated one in a loop.

    Attributes:
        items: Items on this page.
        page: Number of this page, starting at 1.
        limit: Page size that was requested (``per_page`` in the API).
        total: Number of items on all pages.
        total_pages: Number of pages.

    Example:
        ```python
        page = await client.catalog.releases(page=1, limit=25)
        print(f"page {page.page} of {page.total_pages}, {page.total} releases in total")
        for release in page.items:
            print(release.name.main)
        ```
    """

    items: list[T]
    page: int
    limit: int
    total: int
    total_pages: int

    @model_validator(mode="before")
    @classmethod
    def _from_api(cls, data: Any) -> Any:
        """Accept the API's ``{"data": ..., "meta": {"pagination": ...}}`` envelope."""
        if not isinstance(data, dict) or "data" not in data:
            return data
        meta = data.get("meta")
        pagination = meta.get("pagination") if isinstance(meta, dict) else None
        if not isinstance(pagination, dict):
            return data  # leave it to field validation to report what's missing
        return {
            "items": data["data"],
            "page": pagination.get("current_page"),
            "limit": pagination.get("per_page"),
            "total": pagination.get("total"),
            "total_pages": pagination.get("total_pages"),
        }

    @property
    def has_next_page(self) -> bool:
        """Whether there are more pages after this one."""
        return self.page < self.total_pages


async def iterate_pages(
    fetch_page: Callable[[int], Awaitable[Page[T]]], *, start_page: int = 1
) -> AsyncIterator[T]:
    """Yield the items of ``fetch_page(start_page)``, ``fetch_page(start_page + 1)``, ...

    Fetches the next page only once the caller has consumed the current one, and stops after
    the last page or at the first empty page (so a ``total_pages`` that went stale while
    iterating can't cause an endless loop). Stop early by breaking out of the ``async for``.

    Args:
        fetch_page: Coroutine function returning the page with the given number.
        start_page: Number of the first page to fetch.

    Yields:
        Items of every page, in order.
    """
    page_number = start_page
    while True:
        page = await fetch_page(page_number)
        for item in page.items:
            yield item
        if not page.items or not page.has_next_page:
            return
        page_number += 1
