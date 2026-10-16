"""Auth errors of the API against recorded live responses (docs/api-notes.md, "Authentication").

The SDK has no auth methods yet (roadmap 4.2), so these go through ``client.http`` and pin
down what the account endpoints answer without a valid session. No real credentials are
involved: the login attempts use a made-up account.
"""

from __future__ import annotations

import pytest

from aniliberty import AniLiberty, AuthRequiredError, ValidationError

PROFILE = "/accounts/users/me/profile"
LOGIN = "/accounts/users/auth/login"
UNAUTHORIZED = "This action is unauthorized."


@pytest.mark.vcr
async def test_protected_endpoint_without_token_is_403() -> None:
    async with AniLiberty() as client:
        with pytest.raises(AuthRequiredError) as excinfo:
            await client.http.request("GET", PROFILE)

    error = excinfo.value
    assert error.status_code == 403
    assert error.message == UNAUTHORIZED
    assert error.payload == {"message": UNAUTHORIZED}


@pytest.mark.vcr
async def test_invalid_token_is_the_same_403() -> None:
    async with AniLiberty(headers={"Authorization": "Bearer not-a-real-token"}) as client:
        with pytest.raises(AuthRequiredError) as excinfo:
            await client.http.request("GET", PROFILE)

    assert excinfo.value.status_code == 403
    assert excinfo.value.message == UNAUTHORIZED


@pytest.mark.vcr
async def test_invalid_token_does_not_break_public_endpoints() -> None:
    async with AniLiberty(headers={"Authorization": "Bearer not-a-real-token"}) as client:
        status = await client.app.status()

    assert status.is_alive is True


@pytest.mark.vcr
async def test_logout_without_token_is_403() -> None:
    async with AniLiberty() as client:
        with pytest.raises(AuthRequiredError) as excinfo:
            await client.http.request("POST", "/accounts/users/auth/logout")

    assert excinfo.value.status_code == 403


@pytest.mark.vcr
async def test_wrong_credentials_are_401_with_error_field() -> None:
    credentials = {"login": "py-aniliberty-no-such-user", "password": "wrong-password"}
    async with AniLiberty() as client:
        with pytest.raises(AuthRequiredError) as excinfo:
            await client.http.request("POST", LOGIN, json=credentials)

    error = excinfo.value
    assert error.status_code == 401
    assert isinstance(error.payload, dict)
    assert error.payload["token"] is None
    assert error.message == error.payload["error"]
    assert error.message.startswith("Не удалось авторизоваться")


@pytest.mark.vcr
async def test_login_without_credentials_is_422() -> None:
    async with AniLiberty() as client:
        with pytest.raises(ValidationError) as excinfo:
            await client.http.request("POST", LOGIN, json={})

    assert set(excinfo.value.errors) == {"login", "password"}
