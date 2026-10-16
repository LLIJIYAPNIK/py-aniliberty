"""client.me: the profile request, the UserProfile model on edge-case JSON."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from aniliberty import AniLiberty, AuthRequiredError, ResponseParseError, UserProfile

# The shape of a live response (new account: no avatar, no traffic yet).
PROFILE: dict[str, Any] = {
    "id": 799331,
    "login": "test-login",
    "email": "user@example.com",
    "avatar": {
        "preview": None,
        "thumbnail": None,
        "optimized": {"preview": None, "thumbnail": None},
    },
    "nickname": "test-login",
    "torrents": {"passkey": "deadbeef00000000", "uploaded": None, "downloaded": None},
    "is_banned": False,
    "created_at": "2026-10-16T16:31:01+00:00",
    "is_with_video_ads": True,
    "is_with_content_ads": True,
    "is_with_video_ads_always": False,
}


async def fetch_profile(response: httpx.Response) -> tuple[httpx.Request, UserProfile]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return response

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with AniLiberty(http_client=http_client, token="t0k3n") as client:
        profile = await client.me.profile()
    await http_client.aclose()
    return seen[0], profile


async def test_profile_requests_own_profile_with_the_token() -> None:
    request, profile = await fetch_profile(httpx.Response(200, json=PROFILE))

    assert request.method == "GET"
    assert request.url.path == "/api/v1/accounts/users/me/profile"
    assert request.headers["Authorization"] == "Bearer t0k3n"
    assert profile.id == 799331
    assert profile.nickname == "test-login"
    assert profile.created_at is not None
    assert profile.created_at.tzinfo is not None
    assert profile.is_with_ads is None  # in the spec, not in live responses
    assert profile.is_with_video_ads is True


def test_new_account_has_empty_avatar_and_no_traffic() -> None:
    profile = UserProfile.model_validate(PROFILE)

    assert profile.avatar is not None
    assert profile.avatar.preview_url is None
    assert profile.torrents is not None
    assert profile.torrents.uploaded is None
    assert profile.torrents.downloaded is None


def test_avatar_paths_resolve_to_absolute_urls() -> None:
    data = {**PROFILE, "avatar": {"preview": "/storage/users/avatars/1/a.jpg"}}

    profile = UserProfile.model_validate(data)

    assert profile.avatar is not None
    assert profile.avatar.preview_url == "https://aniliberty.top/storage/users/avatars/1/a.jpg"


def test_passkey_is_kept_out_of_repr() -> None:
    profile = UserProfile.model_validate(PROFILE)

    assert profile.torrents is not None
    assert profile.torrents.passkey == "deadbeef00000000"
    assert "deadbeef" not in repr(profile)
    assert "deadbeef" not in str(profile)


def test_minimal_profile() -> None:
    profile = UserProfile.model_validate({"id": 1, "login": "x"})

    assert profile.email is None
    assert profile.avatar is None
    assert profile.torrents is None


async def test_profile_without_valid_session_raises_auth_required() -> None:
    body = {"message": "This action is unauthorized."}

    with pytest.raises(AuthRequiredError) as excinfo:
        await fetch_profile(httpx.Response(403, json=body))

    assert excinfo.value.status_code == 403


async def test_profile_of_unexpected_shape_raises_response_parse_error() -> None:
    with pytest.raises(ResponseParseError) as excinfo:
        await fetch_profile(httpx.Response(200, json={"login": "x"}))

    assert excinfo.value.payload == {"login": "x"}
