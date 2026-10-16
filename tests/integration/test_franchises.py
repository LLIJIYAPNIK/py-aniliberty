"""client.franchises against recorded live responses."""

from __future__ import annotations

import pytest

from aniliberty import AniLiberty, Franchise, NotFoundError

FRIEREN = "sousou-no-frieren"
NO_FRANCHISE_RELEASE = 10324  # a new release that isn't part of any franchise


@pytest.mark.vcr
async def test_list() -> None:
    async with AniLiberty() as client:
        franchises = await client.franchises.list()

    assert len(franchises) > 100
    assert all(isinstance(f, Franchise) and f.id and f.name for f in franchises)
    assert len({f.id for f in franchises}) == len(franchises)
    # The list doesn't include the releases themselves.
    assert all(f.franchise_releases == [] for f in franchises)


@pytest.mark.vcr
async def test_get_by_id_and_by_franchise_object() -> None:
    async with AniLiberty() as client:
        [listed] = await client.franchises.random(limit=1)
        by_object = await client.franchises.get(listed)
        by_id = await client.franchises.get(listed.id)

    assert by_object == by_id
    assert by_object.franchise_releases
    orders = [item.sort_order for item in by_object.franchise_releases]
    assert orders == sorted(orders)
    for item in by_object.franchise_releases:
        assert item.franchise_id == by_object.id
        assert item.release_id == item.release.id


@pytest.mark.vcr
async def test_get_missing_franchise_raises_not_found() -> None:
    async with AniLiberty() as client:
        with pytest.raises(NotFoundError):
            await client.franchises.get("00000000-0000-0000-0000-000000000000")


@pytest.mark.vcr
async def test_random() -> None:
    async with AniLiberty() as client:
        franchises = await client.franchises.random(limit=3)

    assert len(franchises) == 3


@pytest.mark.vcr
async def test_for_release() -> None:
    async with AniLiberty() as client:
        release = await client.releases.get(FRIEREN)
        franchises = await client.franchises.for_release(release)

    [franchise] = franchises
    assert release.id in {item.release_id for item in franchise.franchise_releases}
    assert franchise.franchise_releases[0].release.alias == FRIEREN  # the first season


@pytest.mark.vcr
async def test_for_release_without_franchise_is_empty() -> None:
    async with AniLiberty() as client:
        assert await client.franchises.for_release(NO_FRANCHISE_RELEASE) == []


@pytest.mark.vcr
async def test_for_missing_release_raises_not_found() -> None:
    async with AniLiberty() as client:
        with pytest.raises(NotFoundError):
            await client.franchises.for_release(999999999)
