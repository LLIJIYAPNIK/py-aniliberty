"""client.auth and session errors against recorded live responses.

See docs/api-notes.md, "Authentication". Tests taking the ``credentials`` fixture log in to
the test account; its secrets are scrubbed from the cassettes by conftest. The others use a
made-up account or none.
"""

from __future__ import annotations

import pytest
from conftest import Credentials

from aniliberty import (
    AniLiberty,
    AuthRequiredError,
    IssuedOtp,
    NotFoundError,
    ValidationError,
)

PROFILE = "/accounts/users/me/profile"
UNAUTHORIZED = "This action is unauthorized."
DEVICE_ID = "py-aniliberty-tests-device"


# --- without a session ----------------------------------------------------------------------


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
    async with AniLiberty(token="not-a-real-token") as client:
        with pytest.raises(AuthRequiredError) as excinfo:
            await client.http.request("GET", PROFILE)

    assert excinfo.value.status_code == 403
    assert excinfo.value.message == UNAUTHORIZED


@pytest.mark.vcr
async def test_invalid_token_does_not_break_public_endpoints() -> None:
    async with AniLiberty(token="not-a-real-token") as client:
        status = await client.app.status()

    assert status.is_alive is True


@pytest.mark.vcr
async def test_logout_without_token_is_403() -> None:
    async with AniLiberty() as client:
        with pytest.raises(AuthRequiredError) as excinfo:
            await client.auth.logout()

    assert excinfo.value.status_code == 403
    assert client.token is None


@pytest.mark.vcr
async def test_wrong_credentials_are_401_with_error_field() -> None:
    async with AniLiberty() as client:
        with pytest.raises(AuthRequiredError) as excinfo:
            await client.auth.login(login="py-aniliberty-no-such-user", password="wrong-password")

    error = excinfo.value
    assert error.status_code == 401
    assert isinstance(error.payload, dict)
    assert error.payload["token"] is None
    assert error.message == error.payload["error"]
    assert error.message.startswith("Не удалось авторизоваться")
    assert client.token is None


@pytest.mark.vcr
async def test_login_without_credentials_is_422() -> None:
    async with AniLiberty() as client:
        with pytest.raises(ValidationError) as excinfo:
            await client.auth.login(login="", password="")

    assert set(excinfo.value.errors) == {"login", "password"}


# --- password login -------------------------------------------------------------------------


@pytest.mark.vcr
async def test_login_and_logout(credentials: Credentials) -> None:
    async with AniLiberty() as client:
        session = await client.auth.login(login=credentials.login, password=credentials.password)
        token = client.token
        profile = await client.http.request("GET", PROFILE)
        await client.auth.logout()
        assert client.token is None

        # The logged-out token is rejected like any invalid one.
        client.token = token
        with pytest.raises(AuthRequiredError) as excinfo:
            await client.http.request("GET", PROFILE)

    assert session.token == token
    assert token
    assert isinstance(profile, dict)
    assert profile["login"]
    assert profile["torrents"]["passkey"]
    assert excinfo.value.status_code == 403


@pytest.mark.vcr
async def test_saved_token_reuses_the_session(credentials: Credentials) -> None:
    async with AniLiberty() as first:
        await first.auth.login(login=credentials.login, password=credentials.password)
        saved = first.token

    async with AniLiberty(token=saved) as second:
        profile = await second.http.request("GET", PROFILE)
        await second.auth.logout()

    assert isinstance(profile, dict)
    assert profile["id"]


# --- one-time codes -------------------------------------------------------------------------


@pytest.mark.vcr
async def test_otp_flow(credentials: Credentials) -> None:
    async with AniLiberty() as device, AniLiberty() as phone:
        issued = await device.auth.otp.issue(device_id=DEVICE_ID)

        await phone.auth.login(login=credentials.login, password=credentials.password)
        await phone.auth.otp.accept(issued.otp.code)

        session = await device.auth.otp.login(code=issued.otp.code, device_id=DEVICE_ID)
        device_profile = await device.http.request("GET", PROFILE)

        await device.auth.logout()
        await phone.auth.logout()

    # A code logs in once.
    async with AniLiberty() as another:
        with pytest.raises(NotFoundError):
            await another.auth.otp.login(code=issued.otp.code, device_id=DEVICE_ID)

    assert isinstance(issued, IssuedOtp)
    assert issued.otp.device_id == DEVICE_ID
    assert issued.otp.user_id is None
    assert len(issued.otp.code) == 6
    assert 0 < issued.remaining_time <= 300
    assert session.token
    assert device_profile["id"]


@pytest.mark.vcr
async def test_otp_accept_without_session_is_403() -> None:
    # Checked before the code is looked up, so any code will do.
    async with AniLiberty() as client:
        with pytest.raises(AuthRequiredError):
            await client.auth.otp.accept("123456")


# --- social networks and password recovery --------------------------------------------------


@pytest.mark.vcr
async def test_social_login_returns_oauth_url() -> None:
    async with AniLiberty() as client:
        start = await client.auth.social.login("discord")

    assert start.url.startswith("https://")
    assert start.state
    assert start.state in start.url


@pytest.mark.vcr
async def test_social_authenticate_unknown_state_is_404() -> None:
    # The API answers with an empty text/html 404 — not an anti-bot page.
    async with AniLiberty() as client:
        with pytest.raises(NotFoundError):
            await client.auth.social.authenticate("py-aniliberty-unknown-state")

    assert client.token is None


@pytest.mark.vcr
async def test_password_forget_answers_the_same_for_unknown_email() -> None:
    async with AniLiberty() as client:
        assert await client.auth.password.forget(email="py-aniliberty-nobody@example.com") is None


@pytest.mark.vcr
async def test_password_forget_rejects_malformed_email() -> None:
    async with AniLiberty() as client:
        with pytest.raises(ValidationError) as excinfo:
            await client.auth.password.forget(email="not-an-email")

    assert list(excinfo.value.errors) == ["email"]


@pytest.mark.vcr
async def test_password_reset_with_unknown_token_is_404() -> None:
    async with AniLiberty() as client:
        with pytest.raises(NotFoundError):
            await client.auth.password.reset(token="py-aniliberty-bogus", password="Abcdefgh123!")
