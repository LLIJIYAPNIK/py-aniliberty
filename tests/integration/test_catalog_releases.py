"""client.catalog.releases / iter_releases against recorded live responses.

The assertions check how the filters combine (docs/api-notes.md, "Catalog filters").
"""

from __future__ import annotations

import pytest

from aniliberty import AniLiberty, Page, ValidationError

ACTION, FANTASY = 14, 29  # two genres that often go together


@pytest.mark.vcr
async def test_whole_catalog_first_page() -> None:
    async with AniLiberty() as client:
        page = await client.catalog.releases(limit=5)

    assert isinstance(page, Page)
    assert len(page.items) == 5
    assert page.total > 1000
    assert all(r.genres for r in page.items)
    # Default order: most recently updated first.
    fresh = [r.fresh_at for r in page.items]
    assert fresh == sorted(fresh, reverse=True)  # type: ignore[type-var]


@pytest.mark.vcr
async def test_genres_are_combined_with_and() -> None:
    async with AniLiberty() as client:
        one = await client.catalog.releases(genres=[ACTION], limit=1)
        both = await client.catalog.releases(genres=[ACTION, FANTASY], limit=50)

    assert 0 < both.total < one.total
    assert all({ACTION, FANTASY} <= {g.id for g in r.genres} for r in both.items)


@pytest.mark.vcr
async def test_types_are_combined_with_or() -> None:
    async with AniLiberty() as client:
        tv = await client.catalog.releases(types=["TV"], limit=1)
        movie = await client.catalog.releases(types=["MOVIE"], limit=1)
        either = await client.catalog.releases(types=["TV", "MOVIE"], limit=1)

    assert either.total == tv.total + movie.total


@pytest.mark.vcr
async def test_year_bounds_are_inclusive() -> None:
    async with AniLiberty() as client:
        page = await client.catalog.releases(year_from=2020, year_to=2020, limit=50)

    assert page.total > 0
    assert {r.year for r in page.items} == {2020}


@pytest.mark.vcr
async def test_sorting_by_year() -> None:
    async with AniLiberty() as client:
        page = await client.catalog.releases(sorting="YEAR_ASC", limit=10)

    years = [r.year for r in page.items]
    assert years == sorted(years)  # type: ignore[type-var]


@pytest.mark.vcr
async def test_sorting_by_rating_orders_by_favorites_count() -> None:
    async with AniLiberty() as client:
        page = await client.catalog.releases(sorting="RATING_DESC", limit=10)

    favorites = [r.added_in_users_favorites for r in page.items]
    assert favorites == sorted(favorites, reverse=True)


@pytest.mark.vcr
async def test_search_combined_with_filters() -> None:
    async with AniLiberty() as client:
        page = await client.catalog.releases(search="frieren", types=["TV"])

    assert {r.alias for r in page.items} == {"sousou-no-frieren", "sousou-no-frieren-2nd-season"}


@pytest.mark.vcr
async def test_reference_values_work_as_filters() -> None:
    async with AniLiberty() as client:
        statuses = await client.catalog.references.publish_statuses()
        ongoing = next(s for s in statuses if s.value == "IS_ONGOING")
        page = await client.catalog.releases(publish_statuses=[ongoing], limit=50)

    assert page.total > 0
    assert all(r.is_ongoing for r in page.items)


@pytest.mark.vcr
async def test_page_past_the_end_is_empty() -> None:
    async with AniLiberty() as client:
        page = await client.catalog.releases(page=100000, limit=5)

    assert page.items == []
    assert not page.has_next_page


@pytest.mark.vcr
async def test_limit_above_50_is_rejected_by_the_api() -> None:
    async with AniLiberty() as client:
        with pytest.raises(ValidationError) as excinfo:
            await client.catalog.releases(limit=51)

    assert "limit" in excinfo.value.errors


@pytest.mark.vcr
async def test_iter_releases_walks_all_pages() -> None:
    async with AniLiberty() as client:
        first = await client.catalog.releases(publish_statuses=["IS_ONGOING"], limit=1)
        ids = [
            r.id
            async for r in client.catalog.iter_releases(publish_statuses=["IS_ONGOING"], limit=10)
        ]

    assert len(ids) == first.total
    assert len(set(ids)) == len(ids)
