"""client.me against recorded live responses of the test account.

The account's login, e-mail and passkey are scrubbed from the cassettes by conftest.
"""

from __future__ import annotations

import pytest
from conftest import Credentials

from aniliberty import AniLiberty, AuthRequiredError, UserProfile


@pytest.mark.vcr
async def test_profile(credentials: Credentials) -> None:
    async with AniLiberty() as client:
        await client.auth.login(login=credentials.login, password=credentials.password)
        profile = await client.me.profile()
        await client.auth.logout()

    assert isinstance(profile, UserProfile)
    assert profile.id > 0
    assert profile.login
    assert profile.email is not None
    assert "@" in profile.email
    assert profile.nickname
    assert profile.is_banned is False
    assert profile.created_at is not None
    assert profile.avatar is not None
    assert profile.torrents is not None
    assert profile.torrents.passkey
    # Not in the spec, but sent; the spec's is_with_ads isn't.
    assert profile.is_with_video_ads is not None
    assert profile.is_with_content_ads is not None
    assert profile.is_with_video_ads_always is not None
    assert profile.is_with_ads is None


@pytest.mark.vcr
async def test_profile_without_session_raises_auth_required() -> None:
    async with AniLiberty() as client:
        with pytest.raises(AuthRequiredError) as excinfo:
            await client.me.profile()

    assert excinfo.value.status_code == 403
