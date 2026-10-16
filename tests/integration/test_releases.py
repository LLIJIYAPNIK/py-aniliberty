"""client.releases against recorded live responses."""

from __future__ import annotations

import pytest

from aniliberty import AniLiberty, NotFoundError, Page, Release, ValidationError

RELEASE_ID = 10297
RELEASE_ALIAS = "tensei-shitara-ken-deshita-2nd-season"
OTHER_IDS = [10318, 10324]


@pytest.mark.vcr
async def test_latest() -> None:
    async with AniLiberty() as client:
        releases = await client.releases.latest(limit=3)

    assert len(releases) == 3
    release = releases[0]
    assert isinstance(release, Release)
    assert release.name.main
    assert release.genres
    assert release.poster is not None
    assert release.poster.preview_url is not None
    assert release.poster.preview_url.startswith("https://aniliberty.top/storage/")
    assert release.fresh_at is not None
    assert release.fresh_at.tzinfo is not None


@pytest.mark.vcr
async def test_latest_limit_above_50_is_rejected_by_the_api() -> None:
    async with AniLiberty() as client:
        with pytest.raises(ValidationError) as excinfo:
            await client.releases.latest(limit=51)

    assert "limit" in excinfo.value.errors


@pytest.mark.vcr
async def test_random() -> None:
    async with AniLiberty() as client:
        releases = await client.releases.random(limit=2)

    assert len(releases) == 2
    assert all(isinstance(r.background_covers, list) for r in releases)


@pytest.mark.vcr
async def test_recommended_for_a_release() -> None:
    async with AniLiberty() as client:
        releases = await client.releases.recommended(release_id=RELEASE_ID, limit=2)

    assert len(releases) == 2
    assert RELEASE_ID not in {r.id for r in releases}


@pytest.mark.vcr
async def test_recommended_without_a_release() -> None:
    async with AniLiberty() as client:
        releases = await client.releases.recommended(limit=2)

    assert len(releases) == 2


@pytest.mark.vcr
async def test_get_by_alias_and_by_id_return_the_same_release() -> None:
    async with AniLiberty() as client:
        by_alias = await client.releases.get(RELEASE_ALIAS)
        by_id = await client.releases.get(RELEASE_ID)

    assert by_alias.id == by_id.id == RELEASE_ID
    assert by_alias.alias == RELEASE_ALIAS
    assert by_alias.type is not None
    assert by_alias.type.value == "TV"
    assert by_alias.age_rating is not None
    assert by_alias.age_rating.label == "16+"
    assert by_alias.publish_day is not None
    assert 1 <= by_alias.publish_day.value <= 7
    assert by_alias.members  # the release page includes members
    assert by_alias.rating is not None
    assert set(by_alias.rating.distribution) == set(range(1, 11))
    assert by_alias.shikimori is not None
    assert by_alias.shikimori.url is not None


@pytest.mark.vcr
async def test_get_missing_release_raises_not_found() -> None:
    async with AniLiberty() as client:
        with pytest.raises(NotFoundError):
            await client.releases.get(999999999)


@pytest.mark.vcr
async def test_members() -> None:
    async with AniLiberty() as client:
        members = await client.releases.members(RELEASE_ID)

    assert members
    assert all(m.nickname and m.role for m in members)
    assert "voicing" in {m.role.value for m in members if m.role}


@pytest.mark.vcr
async def test_members_of_missing_release_raise_not_found() -> None:
    async with AniLiberty() as client:
        with pytest.raises(NotFoundError):
            await client.releases.members("this-alias-does-not-exist-xyz")


@pytest.mark.vcr
async def test_list_by_ids_and_aliases_is_paginated_and_deduplicated() -> None:
    async with AniLiberty() as client:
        page = await client.releases.list(
            ids=[RELEASE_ID, *OTHER_IDS], aliases=[RELEASE_ALIAS], limit=2
        )

    assert isinstance(page, Page)
    assert page.total == 3  # RELEASE_ID requested twice, returned once
    assert page.total_pages == 2
    assert len(page.items) == 2
    assert page.has_next_page


@pytest.mark.vcr
async def test_iter_list_walks_all_pages() -> None:
    async with AniLiberty() as client:
        ids = [r.id async for r in client.releases.iter_list(ids=[RELEASE_ID, *OTHER_IDS], limit=2)]

    assert sorted(ids) == sorted([RELEASE_ID, *OTHER_IDS])
