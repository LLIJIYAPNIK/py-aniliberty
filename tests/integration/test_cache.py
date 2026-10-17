"""The response cache against recorded live responses.

Each cassette holds one response per request: a repeated call that reached the API instead of
the cache would find nothing to replay and fail.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aniliberty import AniLiberty

RELEASE_ID = 9839  # the release from the issue that asked for the cache (a franchise member)


@pytest.mark.vcr
async def test_repeated_calls_are_answered_from_the_cache(tmp_path: Path) -> None:
    async with AniLiberty(cache_dir=tmp_path, cache_ttl=6 * 3600) as client:
        franchises = await client.franchises.for_release(RELEASE_ID)
        found = await client.app.search_releases("frieren")

        assert await client.franchises.for_release(RELEASE_ID) == franchises
        assert await client.app.search_releases("frieren") == found

    assert franchises
    assert any(r.alias == "sousou-no-frieren" for r in found)
    assert len(list(tmp_path.glob("*.json"))) == 2


@pytest.mark.vcr
async def test_cache_survives_the_client(tmp_path: Path) -> None:
    async with AniLiberty(cache_dir=tmp_path) as client:
        release = await client.releases.get(RELEASE_ID)

    async with AniLiberty(cache_dir=tmp_path) as client:
        assert await client.releases.get(RELEASE_ID) == release


@pytest.mark.vcr
async def test_refresh_goes_to_the_api(tmp_path: Path) -> None:
    async with AniLiberty(cache_dir=tmp_path) as client:
        first = await client.genres.list()
        refreshed = await client.genres.list(refresh=True)
        cached = await client.genres.list()

    # Recorded as two requests: the first call and the refresh; the last one is the cache.
    assert [g.id for g in first] == [g.id for g in refreshed] == [g.id for g in cached]
