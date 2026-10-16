"""client.me.favorites against recorded live responses of the test account.

The scenario starts and ends with empty favorites. Releases used (as of 2026-10-16):
9839 (TV, 2025), 9600 (TV, 2024), 8030 (TV, 2019); all three have genres 14 and 27, only
8030 has genre 8.
"""

from __future__ import annotations

import pytest
from conftest import Credentials

from aniliberty import AniLiberty, AuthRequiredError, Release

NEWEST, MIDDLE, OLDEST = 9839, 9600, 8030
MISSING = 99999999


@pytest.mark.vcr
async def test_favorites_lifecycle(credentials: Credentials) -> None:
    async with AniLiberty() as client:
        await client.auth.login(login=credentials.login, password=credentials.password)
        favorites = client.me.favorites
        try:
            assert await favorites.ids() == []
            assert await favorites.references.years() == []

            ids = await favorites.add(NEWEST, OLDEST)
            assert ids == [NEWEST, OLDEST]
            # Duplicates are skipped; a Release object works as well as an ID.
            middle = await client.releases.get(MIDDLE)
            assert await favorites.add(OLDEST, middle) == [NEWEST, OLDEST, MIDDLE]

            by_year = await favorites.releases(sorting="YEAR_DESC")
            assert [r.id for r in by_year.items] == [NEWEST, MIDDLE, OLDEST]
            assert by_year.total == 3
            assert all(isinstance(r, Release) and r.genres for r in by_year.items)
            assert by_year.items[0].episodes

            two_years = await favorites.releases(years=[2024, 2019])
            assert {r.id for r in two_years.items} == {MIDDLE, OLDEST}
            only_8 = await favorites.releases(genres=[14, 8])
            assert [r.id for r in only_8.items] == [OLDEST]
            assert (await favorites.releases(types=["MOVIE"])).items == []

            assert await favorites.references.years() == [2025, 2024, 2019]
            assert [t.value for t in await favorites.references.types()] == ["TV"]
            genres = {g.id for g in await favorites.references.genres()}
            assert {8, 14, 27} <= genres
            sorting = [s.value for s in await favorites.references.sorting()]
            assert "CREATED_AT_DESC" in sorting

            walked = [r.id async for r in favorites.iter_releases(sorting="YEAR_ASC", limit=1)]
            assert walked == [OLDEST, MIDDLE, NEWEST]

            # A release that doesn't exist is accepted into the IDs but never listed.
            assert MISSING in await favorites.add(MISSING)
            assert (await favorites.releases()).total == 3

            assert await favorites.remove(NEWEST, NEWEST) == [OLDEST, MIDDLE, MISSING]
        finally:
            left = await favorites.ids()
            if left:
                await favorites.remove(*left)
            assert await favorites.ids() == []
            await client.auth.logout()


@pytest.mark.vcr
async def test_favorites_without_session_raise_auth_required() -> None:
    async with AniLiberty() as client:
        with pytest.raises(AuthRequiredError) as excinfo:
            await client.me.favorites.ids()

    assert excinfo.value.status_code == 403
