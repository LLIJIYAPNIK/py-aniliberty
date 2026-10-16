"""client.app.search_releases against recorded live responses."""

from __future__ import annotations

import pytest

from aniliberty import AniLiberty, Release, ValidationError

FRIEREN_ALIAS = "sousou-no-frieren"


@pytest.mark.vcr
@pytest.mark.parametrize(
    "query", ["frieren", "Фрирен", FRIEREN_ALIAS], ids=["english", "russian", "alias"]
)
async def test_search_finds_a_release_by_any_of_its_names(query: str) -> None:
    async with AniLiberty() as client:
        releases = await client.app.search_releases(query)

    assert releases
    assert all(isinstance(r, Release) for r in releases)
    assert FRIEREN_ALIAS in {r.alias for r in releases}


@pytest.mark.vcr
async def test_search_results_have_no_endpoint_extras() -> None:
    async with AniLiberty() as client:
        releases = await client.app.search_releases("naruto")

    assert releases
    assert all(r.genres == [] and r.episodes == [] for r in releases)
    assert all(r.poster is not None for r in releases)


@pytest.mark.vcr
async def test_search_without_matches_returns_an_empty_list() -> None:
    async with AniLiberty() as client:
        assert await client.app.search_releases("zzzzqqqxx") == []


@pytest.mark.vcr
async def test_empty_query_is_rejected_by_the_api() -> None:
    async with AniLiberty() as client:
        with pytest.raises(ValidationError) as excinfo:
            await client.app.search_releases("")

    assert "query" in excinfo.value.errors
