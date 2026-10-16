"""client.me.collections against recorded live responses of the test account.

The scenario starts and ends with empty collections. Releases used (as of 2026-10-16):
9839 (TV, 2025), 9600 (TV, 2024), 8030 (TV, 2019); all three have genres 14 and 27, only
8030 has genre 8.
"""

from __future__ import annotations

import pytest
from conftest import Credentials

from aniliberty import AniLiberty, AuthRequiredError, CollectionItem, ValidationError

NEWEST, MIDDLE, OLDEST = 9839, 9600, 8030


@pytest.mark.vcr
async def test_collections_lifecycle(credentials: Credentials) -> None:
    async with AniLiberty() as client:
        await client.auth.login(login=credentials.login, password=credentials.password)
        collections = client.me.collections
        try:
            assert await collections.ids() == []

            items = await collections.add(OLDEST, MIDDLE, NEWEST, to="PLANNED")
            assert {item.release_id for item in items} == {OLDEST, MIDDLE, NEWEST}
            assert {item.collection for item in items} == {"PLANNED"}

            # A release is in one collection at most: adding it elsewhere moves it.
            items = await collections.add(NEWEST, to="WATCHED")
            where = {item.release_id: item.collection for item in items}
            assert where == {OLDEST: "PLANNED", MIDDLE: "PLANNED", NEWEST: "WATCHED"}
            assert await collections.ids() == items

            planned = await collections.releases("PLANNED")
            assert {r.id for r in planned.items} == {OLDEST, MIDDLE}
            assert planned.total == 2
            assert all(r.genres for r in planned.items)
            assert [r.id for r in (await collections.releases("WATCHED")).items] == [NEWEST]
            assert (await collections.releases("ABANDONED")).items == []

            assert [r.id for r in (await collections.releases("PLANNED", years=[2024])).items] == [
                MIDDLE
            ]
            only_8 = await collections.releases("PLANNED", genres=[14, 8])
            assert [r.id for r in only_8.items] == [OLDEST]
            assert (await collections.releases("PLANNED", types=["MOVIE"])).items == []

            walked = [r.id async for r in collections.iter_releases("PLANNED", limit=1)]
            assert sorted(walked) == sorted([OLDEST, MIDDLE])

            # The references cover all collections together.
            assert await collections.references.years() == [2025, 2024, 2019]
            assert [t.value for t in await collections.references.types()] == ["TV"]
            assert {8, 14, 27} <= {g.id for g in await collections.references.genres()}
            assert [a.value for a in await collections.references.age_ratings()] == ["R16_PLUS"]

            # Collections and favorites are separate.
            assert await client.me.favorites.ids() == []

            items = await collections.remove(NEWEST, NEWEST)
            assert items == [
                CollectionItem(release_id=OLDEST, collection="PLANNED"),
                CollectionItem(release_id=MIDDLE, collection="PLANNED"),
            ]
        finally:
            left = await collections.ids()
            if left:
                await collections.remove(*(item.release_id for item in left))
            assert await collections.ids() == []
            await client.auth.logout()


@pytest.mark.vcr
async def test_page_size_above_50_is_rejected_by_the_api(credentials: Credentials) -> None:
    async with AniLiberty() as client:
        await client.auth.login(login=credentials.login, password=credentials.password)
        try:
            with pytest.raises(ValidationError) as excinfo:
                await client.me.collections.releases("PLANNED", limit=51)
        finally:
            await client.auth.logout()

    assert list(excinfo.value.errors) == ["limit"]


@pytest.mark.vcr
async def test_collections_without_session_raise_auth_required() -> None:
    async with AniLiberty() as client:
        with pytest.raises(AuthRequiredError) as excinfo:
            await client.me.collections.ids()

    assert excinfo.value.status_code == 403
