"""client.releases.ratings against recorded live responses of the test account.

Release 8030 is rated and unrated again; the scenario starts and ends without a score.
"""

from __future__ import annotations

import pytest
from conftest import Credentials

from aniliberty import AniLiberty, AuthRequiredError, NotFoundError, UserRating

RELEASE = 8030
MISSING = 99999999


@pytest.mark.vcr
async def test_rating_lifecycle(credentials: Credentials) -> None:
    async with AniLiberty() as client:
        await client.auth.login(login=credentials.login, password=credentials.password)
        ratings = client.releases.ratings
        try:
            assert await ratings.get(RELEASE) == UserRating(release_id=RELEASE, score=None)

            assert (await ratings.set(RELEASE, score=7)).score == 7
            # Setting again replaces the score.
            release = await client.releases.get(RELEASE)
            assert await ratings.set(release, score=9) == UserRating(release_id=RELEASE, score=9)
            assert (await ratings.get(RELEASE)).score == 9

            assert (await ratings.remove(RELEASE)).score is None
            # Removing again is a no-op.
            assert (await ratings.remove(RELEASE)).score is None
            assert (await ratings.get(RELEASE)).score is None

            with pytest.raises(NotFoundError):
                await ratings.get(MISSING)
        finally:
            await ratings.remove(RELEASE)
            await client.auth.logout()


@pytest.mark.vcr
async def test_ratings_without_session_raise_auth_required() -> None:
    async with AniLiberty() as client:
        with pytest.raises(AuthRequiredError) as excinfo:
            await client.releases.ratings.get(RELEASE)

    assert excinfo.value.status_code == 403
