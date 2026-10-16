"""client.catalog.references against recorded live responses."""

from __future__ import annotations

import pytest

from aniliberty import AgeRating, AniLiberty, Genre, SortingOption, ValueDescription


@pytest.mark.vcr
async def test_genres() -> None:
    async with AniLiberty() as client:
        genres = await client.catalog.references.genres()

    assert len(genres) > 10
    assert all(isinstance(g, Genre) and g.id > 0 and g.name for g in genres)
    assert len({g.id for g in genres}) == len(genres)
    # This list carries only id and name.
    assert all(g.image is None and g.total_releases is None for g in genres)


@pytest.mark.vcr
async def test_types() -> None:
    async with AniLiberty() as client:
        types = await client.catalog.references.types()

    assert all(isinstance(t, ValueDescription) and t.description for t in types)
    # The values of the spec enum enums.anime.releases.release.type.
    assert {t.value for t in types} == {
        "TV", "ONA", "WEB", "OVA", "OAD", "MOVIE", "DORAMA", "SPECIAL"
    }  # fmt: skip


@pytest.mark.vcr
async def test_seasons() -> None:
    async with AniLiberty() as client:
        seasons = await client.catalog.references.seasons()

    assert [s.value for s in seasons] == ["winter", "spring", "summer", "autumn"]


@pytest.mark.vcr
async def test_years() -> None:
    async with AniLiberty() as client:
        years = await client.catalog.references.years()

    assert years == sorted(years)
    assert all(isinstance(y, int) for y in years)
    assert 2020 in years


@pytest.mark.vcr
async def test_age_ratings() -> None:
    async with AniLiberty() as client:
        ratings = await client.catalog.references.age_ratings()

    assert all(isinstance(r, AgeRating) for r in ratings)
    assert [r.label for r in ratings] == ["0+", "6+", "12+", "16+", "18+"]
    assert all(r.is_adult is None for r in ratings)  # not part of this list


@pytest.mark.vcr
async def test_publish_and_production_statuses() -> None:
    async with AniLiberty() as client:
        publish = await client.catalog.references.publish_statuses()
        production = await client.catalog.references.production_statuses()

    assert {s.value for s in publish} == {"IS_ONGOING", "IS_NOT_ONGOING"}
    assert {s.value for s in production} == {"IS_IN_PRODUCTION", "IS_NOT_IN_PRODUCTION"}


@pytest.mark.vcr
async def test_sorting() -> None:
    async with AniLiberty() as client:
        options = await client.catalog.references.sorting()

    assert all(isinstance(o, SortingOption) and o.label and o.description for o in options)
    assert "FRESH_AT_DESC" in {o.value for o in options}
